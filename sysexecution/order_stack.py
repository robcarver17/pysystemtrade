from copy import copy
from syscore.objects import (
    missing_order,
    success,
    failure,
    locked_order,
    duplicate_order,
    no_order_id,
    no_children,
    no_parent,
    order_is_in_status_finished,
    zero_order,
)

from syslogdiag.log import logtoscreen


class orderStackData(object):
    """
    An order stack is designed to hold orders.
    This is a base class, specific stacks are used for virtual and contract level stacks

    Will also inherit from this for specific implementations, eg mongo

    What kind of stuff do we do in stacks:
     - put an order on the stack, where no order existed
     - modify: put an order on the stack which replaces an existing order
     - view an order with certain characteristics from the stack
     - get an order from the stack with the intention of executing it. This also locks the order.
     - 'lock' an order so it can't be modified, 'gotten' or removed
     - unlock an order
     - remove a filled or cancelled order from the stack
     - empty the stack entirely (done at the end of every day)
     - view all the orders on the stack

     Stacks are pure state and so don't need archive data creating

     This kind of stack doesn't have to worry about partial executions
     If a partial is generated then the entire order will be removed, and on the next cycle
         a new order generated which will include the net order unless something has changed

    """

    def __init__(self, log=logtoscreen("order-stack")):
        self.log = log
        self._stack = dict()

    def __repr__(self):
        return "Order stack: %s" % str(self._stack)

    def put_list_of_orders_on_stack(
            self,
            list_of_orders,
            unlock_when_finished=True):
        """
        Put a list of new orders on the stack. We lock these before placing on.

        If any do not return order_id (so something has gone wrong) we remove all the relevant orders and return failure

        If all work out okay, we unlock the orders

        We may choose not to unlock the orders, if for example we're doing a transaction that involves
           adding something to another stack

        :param list_of_orders:
        :return: list of order_ids or failure
        """
        if len(list_of_orders) == 0:
            return []

        list_of_order_ids = []
        status = success
        for order in list_of_orders:
            log = order.log_with_attributes(self.log)
            order.lock_order()
            order_id = self.put_order_on_stack(order)
            if not isinstance(order_id, int):
                log.warn(
                    "Failed to put contract order %s on stack error %s, rolling back entire transaction" %
                    (str(order), str(order_id)))
                status = failure
                break

            else:
                list_of_order_ids.append(order_id)

        # At this point we either have total failure (list_of_child_ids is empty, status failure),
        #    or partial failure (list of child_ids is part filled, status failure)
        #    or total success

        if status is failure:
            # rollback the orders we added
            self.rollback_list_of_orders_on_stack(list_of_order_ids)
            return failure

        # success
        if unlock_when_finished:
            self.unlock_list_of_orders(list_of_order_ids)

        return list_of_order_ids

    def rollback_list_of_orders_on_stack(self, list_of_order_ids):
        if len(list_of_order_ids) == 0:
            return success

        self.log.warn(
            "Rolling back addition of orders %s" %
            str(list_of_order_ids))
        for order_id in list_of_order_ids:
            self._unlock_order_on_stack(order_id)
            self.deactivate_order(order_id)
            self.remove_order_with_id_from_stack(order_id)

        return success

    def unlock_list_of_orders(self, list_of_order_ids):
        for order_id in list_of_order_ids:
            self._unlock_order_on_stack(order_id)

        return success

    def put_order_on_stack(self, new_order):
        """
        Put an order on the stack

        :param new_order: Order
        :return: order_id or failure condition: duplicate_order, failure
        """
        order_id_or_error = self._put_order_on_stack_and_get_order_id(
            new_order)

        return order_id_or_error

    # FIND AND LIST ORDERS
    def get_order_with_key_from_stack(self, order_key):
        order_ids = self._get_list_of_orders_with_key_from_stack(
            order_key, exclude_inactive_orders=True
        )
        if len(order_ids) == 0:
            return missing_order
        try:
            assert len(order_ids) == 1
        except BaseException:
            msg = "Multiple orders for key %s shouldn't happen (EXCEPTION)" % order_key
            self.log.critical(msg)
            raise Exception(msg)

        order_id = order_ids[0]
        order = self.get_order_with_id_from_stack(order_id)

        return order

    def get_order_with_id_from_stack(self, order_id):
        # probably will be overriden in data implementation

        order = self._stack.get(order_id, missing_order)

        return order

    def get_list_of_orders_from_order_id_list(self, list_of_order_ids):
        order_list = []
        for order_id in list_of_order_ids:
            order = self.get_order_with_id_from_stack(order_id)
            order_list.append(order)
        return order_list

    def get_list_of_order_ids(self, exclude_inactive_orders=True):
        order_ids = self._get_list_of_all_order_ids()

        if exclude_inactive_orders:
            all_orders = [self.get_order_with_id_from_stack(
                order_id) for order_id in order_ids]
            order_ids = [
                order.order_id for order in all_orders if order.active]

        return order_ids

    def list_of_new_orders(self):
        order_ids = self.get_list_of_order_ids()
        new_order_ids = [
            order_id for order_id in order_ids if self.is_new_order(order_id)
        ]

        return new_order_ids

    def is_new_order(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return False
        if existing_order.children is not no_children:
            return False
        if not existing_order.active:
            return False
        if not existing_order.fill_equals_zero():
            return False

        return True

    def list_of_completed_orders(
        self, allow_partial_completions=False, allow_zero_completions=False
    ):
        order_ids = self.get_list_of_order_ids()
        completed_order_ids = [
            order_id
            for order_id in order_ids
            if self.is_completed(
                order_id,
                allow_partial_completions=allow_partial_completions,
                allow_zero_completions=allow_zero_completions,
            )
        ]

        return completed_order_ids

    def is_completed(
            self,
            order_id,
            allow_partial_completions=False,
            allow_zero_completions=False):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return False
        elif allow_zero_completions:
            return True
        elif allow_partial_completions:
            return not existing_order.fill_equals_zero()
        else:
            return existing_order.fill_equals_desired_trade()

    # CHILD ORDERS
    def add_children_to_order(self, order_id, new_children):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return missing_order

        if existing_order.children is not no_children:
            # can't do this, already have children
            return failure

        new_order = copy(existing_order)
        new_order.children = new_children

        result = self._change_order_on_stack(order_id, new_order)

        return result

    def add_another_child_to_order(self, order_id, new_child):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return missing_order
        existing_order.add_another_child(new_child)

        result = self._change_order_on_stack(order_id, existing_order)

        return result

    def remove_children_from_order(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return missing_order

        new_order = copy(existing_order)
        new_order.remove_children()

        result = self._change_order_on_stack(order_id, new_order)

        return result

    # FILLS
    def change_fill_quantity_for_order(
        self, order_id, fill_qty, filled_price=None, fill_datetime=None
    ):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn(
                "Can't apply fill to non existent order %d" %
                order_id)
            return missing_order

        if existing_order.fill == fill_qty:
            # nout to do here
            return success

        log = self.log.setup(
            strategy_name=existing_order.strategy_name,
            instrument_code=existing_order.instrument_code,
            instrument_order_id=order_id,
        )

        new_order = copy(existing_order)
        try:
            new_order.fill_order(
                fill_qty,
                filled_price=filled_price,
                fill_datetime=fill_datetime)
        except Exception as e:
            log.warn(str(e))
            return failure

        result = self._change_order_on_stack(order_id, new_order)

        log.msg(
            "Changed fill qty from %s to %s for order %s"
            % (str(existing_order.fill), str(fill_qty), str(existing_order))
        )

        return result

    def zero_out(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn("Can't deactivate non existent order" % order_id)
            return missing_order

        log = self.log.setup(
            strategy_name=existing_order.strategy_name,
            instrument_code=existing_order.instrument_code,
            instrument_order_id=order_id,
        )

        if not existing_order.active:
            # already inactive
            return failure

        new_order = copy(existing_order)
        new_order.zero_out()

        # This will fail if being modified or locked
        result = self._change_order_on_stack(
            order_id, new_order, check_if_inactive=False
        )

        return result

    # DEACTIVATE ORDER (Because filled or cancelled)

    def deactivate_order(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn("Can't deactivate non existent order" % order_id)
            return missing_order

        log = self.log.setup(
            strategy_name=existing_order.strategy_name,
            instrument_code=existing_order.instrument_code,
            instrument_order_id=order_id,
        )

        if not existing_order.active:
            # already inactive
            return failure

        new_order = copy(existing_order)
        new_order.deactivate()

        # This will fail if being modified or locked
        result = self._change_order_on_stack(
            order_id, new_order, check_if_inactive=False
        )

        return result

    # REMOVE DEACTIVATED ORDERS (SPRING CLEANING - SHOULD BE ARCHIVED)

    def remove_all_deactivated_orders_from_stack(self):
        inactive_orders = self.get_list_of_inactive_order_ids()
        for order_id in inactive_orders:
            self.remove_order_with_id_from_stack(order_id)

        return success

    def get_list_of_inactive_order_ids(self):
        all_order_ids = self._get_list_of_all_order_ids()
        all_orders = [self.get_order_with_id_from_stack(
            order_id) for order_id in all_order_ids]
        order_ids = [
            order.order_id for order in all_orders if not order.active]

        return order_ids

    def remove_order_with_id_from_stack(self, order_id):
        order_on_stack = self.get_order_with_id_from_stack(order_id)
        if order_on_stack is missing_order:
            raise Exception(
                "Can't remove non existent order %s from stack" %
                order_id)
        if order_on_stack.is_order_locked():
            raise Exception(
                "Can't remove locked order %s from stack" %
                order_on_stack)
        if order_on_stack.active:
            raise Exception(
                "Can't remove active order %s from stack" %
                order_on_stack)

        self._remove_order_with_id_from_stack_no_checking(order_id)

        return success

    # CHANGING AN ORDER ON THE STACK

    def _change_order_on_stack(
            self,
            order_id,
            new_order,
            check_if_inactive=True):
        # Make any kind of general change to an order, checking for locks
        # Doesn't check for other conditions, eg beingactive or not

        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn(
                "Can't change non existent order %d" % order_id,
                instrument_order_id=order_id,
            )
            return missing_order

        log = self.log.setup(
            strategy_name=existing_order.strategy_name,
            instrument_code=existing_order.instrument_code,
            instrument_order_id=order_id,
        )

        lock_status = existing_order.is_order_locked()
        if lock_status is True:
            # already locked can't change
            log.warn("Can't change locked order %s" % str(existing_order))
            return locked_order

        if check_if_inactive:
            if not existing_order.active:
                log.warn(
                    "Can't change order %s as inactive" %
                    str(existing_order))

        result = self._change_order_on_stack_no_checking(order_id, new_order)

        return result

    def _unlock_order_on_stack(self, order_id):
        order = self.get_order_with_id_from_stack(order_id)
        if order is missing_order:
            raise Exception("Non existent order can't lock")
        order.unlock_order()
        self._change_order_on_stack_no_checking(order_id, order)
        return success

    def _lock_order_on_stack(self, order_id):
        order = self.get_order_with_id_from_stack(order_id)
        if order is missing_order:
            raise Exception("Non existent order can't lock")
        order.lock_order()
        self._change_order_on_stack_no_checking(order_id, order)
        return success

    # LOW LEVEL PUT AND CHANGE ORDERS

    def _change_order_on_stack_no_checking(self, order_id, order):
        #
        # probably will be overriden in data implementation

        self._stack[order_id] = order

        return success

    def _put_order_on_stack_and_get_order_id(self, order):
        # We only zero order trades if they are modifying an existing trade,
        # otherwise pointless

        if order.order_id is no_order_id:
            pass
        else:
            self.log.warn(
                "Order %s already has order ID will be ignored" %
                str(order))
        order_to_add = copy(order)
        order_id = self._get_next_order_id()
        order_to_add.order_id = order_id

        result = self._put_order_on_stack_no_checking(order_to_add)
        if result is success:
            return order_id
        else:
            return result

    def _put_order_on_stack_no_checking(self, order):
        # probably will be overriden in data implementation

        order_id = order.order_id
        self._stack[order_id] = order
        return success

    # ORDER ID

    def _get_next_order_id(self):
        # MUST override in data implementation
        # The maximum orderid should ideally live on in permanent storage
        # Otherwise we rely on this stack persisting while downstream stacks
        # rely on mapping orderids

        order_id_on_stack = self.get_list_of_order_ids()
        if len(order_id_on_stack) == 0:
            return 1

        max_order_id_on_stack = max(order_id_on_stack)

        return max_order_id_on_stack + 1

    # FINDING ORDERS AND LIST OF ORDERS

    def _get_order_with_same_tradeable_object_on_stack(self, order):
        """
        Try and get an order with the same tradeable object off the stack

        :param order: Order to check
        :return: Existing order or missing_order or identical_order
        """
        order_key = order.key
        existing_orders = self._get_list_of_orders_with_key_from_stack(
            order_key)
        if len(existing_orders) == 0:
            return missing_order

        return existing_orders

    def _get_list_of_orders_with_key_from_stack(
        self, order_key, exclude_inactive_orders=True
    ):

        all_order_ids = self.get_list_of_order_ids(
            exclude_inactive_orders=exclude_inactive_orders
        )
        all_orders = [self.get_order_with_id_from_stack(
            order_id) for order_id in all_order_ids]
        order_ids = [
            order.order_id for order in all_orders if order.key == order_key]

        return order_ids

    def _get_list_of_all_order_ids(self):
        # probably will be overriden in data implementation
        return list(self._stack.keys())

    # deleting

    def _remove_order_with_id_from_stack_no_checking(self, order_id):
        # probably will be overriden in data implementation

        self._stack.pop(order_id)
        return success

    def _delete_entire_stack_without_checking(self):
        order_id_list = self.get_list_of_order_ids(
            exclude_inactive_orders=False)
        for order_id in order_id_list:
            self._remove_order_with_id_from_stack_no_checking(order_id)

        return success
