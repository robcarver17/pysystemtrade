from copy import copy
from syscore.objects import missing_order, success, failure, locked_order, duplicate_order, no_order_id, no_children, no_parent, order_is_in_status_finished
from syscore.objects import order_is_in_status_modified, order_is_in_status_reject_modification, order_is_in_status_finished

from syslogdiag.log import logtoscreen


class orderStackData(object):
    """
    An order stack is designed to hold orders.
    This is a base class, specific stacks are used for virtual and contract level stacks

    Will also inherit from this for specific implementations, eg mongo

    What kind of stuff do we do in stacks:
     - put an order on the stack, where no order existed
     - modify: put an order on the stack which replaces an existing order
     - put an identical order on the stack, does nothing
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

    def __init__(self, log = logtoscreen("order-stack")):
        self.log = log
        self._stack = dict()

    def __repr__(self):
        return "Order stack: %s" % str(self._stack)

    def put_order_on_stack(self, new_order, modify_existing_order = False, allow_zero_orders=False):
        """
        Put an order on the stack, or at least try to:
        - if no existing order, add
        - if an existing order exists:
            - and locked, don't allow
            - if unlocked:
                 - order is identical, do nothing
                 - order is not identical, update

        :param new_order: Order
        :return: order_id or failure condition: duplicate_order, failure
        """
        if new_order.is_zero_trade() and not allow_zero_orders:
            return failure

        log = self.log.setup(strategy_name=new_order.strategy_name, instrument_code=new_order.instrument_code)

        existing_order = self._get_order_with_same_tradeable_object_on_stack(new_order)
        if existing_order is duplicate_order:
            # Do nothing, pointless
            log.msg("Order %s already on %s" % (str(new_order), self.__repr__()))
            return duplicate_order

        if existing_order is missing_order:
            log.msg("New order %s putting on %s" % (str(new_order), self.__repr__()))
            order_id_or_error = self._put_order_on_stack_and_get_order_id(new_order)
            return order_id_or_error

        existing_order_id = existing_order.order_id
        if not modify_existing_order:
            log.msg("Order %s matches existing order_id %d on %s: " %
                    (str(new_order), existing_order_id, self.__repr__()))
            return duplicate_order

        # Existing order needs modifying
        log.msg("Order %s matches existing order_id %d on %s, trying to modify" %
                (str(new_order), existing_order_id, self.__repr__()))

        result = self.modify_order_on_stack(existing_order_id, new_order.trade)

        if result is success:
            return existing_order_id
        else:
            return result

    def cancel_order(self, order_id):
        """
        Cancels an order by trying to modify quantity to zero or fill, whichever is higher

        Will not cancel child orders; the modification will need to be applied to them also

        :param order_id:
        :return: success or failure
        """
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.msg("Can't cancel non existent order %d" % order_id)
            return failure

        filled_so_far = existing_order.fill
        result = self.modify_order_on_stack(order_id, filled_so_far)

        return result

    # FIND AND LIST ORDERS
    def get_order_with_key_from_stack(self, order_key):
        order_ids = self._get_list_of_orders_with_key_from_stack(order_key, exclude_inactive_orders = True)
        if len(order_ids)==0:
            return missing_order
        try:
            assert len(order_ids)==1
        except:
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

    def get_list_of_order_ids(self, exclude_inactive_orders = True):
        order_ids = self._get_list_of_all_order_ids()

        if exclude_inactive_orders:
            all_orders = [self.get_order_with_id_from_stack(order_id) for order_id in order_ids]
            order_ids = [order.order_id for order in all_orders if order.active]


        return order_ids

    def list_of_new_orders(self):
        order_ids = self.get_list_of_order_ids()
        new_order_ids = [order_id for order_id in order_ids if self.is_new_order(order_id)]

        return new_order_ids


    def is_new_order(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return  False
        if not existing_order.children is no_children:
            return False
        if not existing_order.active:
            return False
        if not existing_order.fill_equals_zero():
            return False
        if existing_order.is_order_in_modification_states():
            return False

        return True

    def list_of_being_modified_orders(self):
        order_ids = self.get_list_of_order_ids()
        order_ids = [order_id for order_id in order_ids if self.is_being_modified(order_id)]

        return order_ids

    def is_being_modified(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return  False
        return existing_order.is_order_being_modified()

    def list_of_finished_modifiying_orders(self):
        order_ids = self.get_list_of_order_ids()
        order_ids = [order_id for order_id in order_ids if self.is_finished_modified(order_id)]

        return order_ids

    def is_finished_modified(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return  False
        return existing_order.is_order_finished_modifying()

    def list_of_rejected_modifying_orders(self):
        order_ids = self.get_list_of_order_ids()
        order_ids = [order_id for order_id in order_ids if self.is_rejected_modified(order_id)]

        return order_ids

    def is_rejected_modified(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return  False
        return existing_order.is_order_modification_rejected()

    def list_of_completed_orders(self):
        order_ids = self.get_list_of_order_ids()
        order_ids = [order_id for order_id in order_ids if self.is_completed(order_id)]

        return order_ids

    def is_completed(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return  False
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

    def remove_children_from_order(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            return missing_order

        new_order = copy(existing_order)
        new_order.remove_children()

        result = self._change_order_on_stack(order_id, new_order)

        return result

    # MODIFYING ORDERS


    def modify_order_on_stack(self, order_id, new_trade):
        """
        Make a change of quantity to an order on the stack
        This is a 3 phase process

        :param existing_order: an existing order, with order_id
        :param new_trade: int
        :return: order_id, because if we are passing up to put order on stack. or failure
        """

        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn("Can't modify non existent order %d" % order_id)
            return missing_order

        log = self.log.setup(strategy_name=existing_order.strategy_name,
                             instrument_code=existing_order.instrument_code
                             )

        modified_order = copy(existing_order)
        modify_status = modified_order.modify_order(new_trade)
        if modify_status is order_is_in_status_reject_modification:
            log.warn("Order %s modification rejected (already filled more than modified quantity)"
                          % (str(existing_order)))
            return order_is_in_status_reject_modification

        if modify_status in [order_is_in_status_finished, order_is_in_status_finished]:
            log.warn("Order %s is already in the process of being modified, can't modify again until cleared"
                          % (str(existing_order)))
            return modify_status

        result = self._change_order_on_stack(existing_order.order_id, modified_order)

        return result

    def completed_modifying_order_on_stack(self, order_id):
        """
        Make a change of quantity to an order on the stack
        This is a 3 phase process
        This is phase two. We can do this once all of our children have finished being modified

        :param existing_order: an existing order, with order_id
        :return:
        """
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn("Can't modify non existent order %d" % order_id)
            return missing_order

        log = self.log.setup(strategy_name=existing_order.strategy_name,
                             instrument_code=existing_order.instrument_code
                             )

        modified_order = copy(existing_order)
        modify_status = modified_order.modification_complete()
        if modify_status is not success:
            log("Can't complete a modification when order is not being modified order %d" % order_id)
            return failure

        result = self._change_order_on_stack(existing_order.order_id, modified_order,
                                             check_if_orders_being_modified=False)

        return result

    def reject_order_on_stack(self, order_id):
        """
        Make a change of quantity to an order on the stack
        This is a 3 phase process
        This is phase two. Will be trigerred if children are rejected.

        :param existing_order: an existing order, with order_id
        :return:
        """
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn("Can't reject non existent order %d" % order_id)
            return missing_order

        log = self.log.setup(strategy_name=existing_order.strategy_name,
                             instrument_code=existing_order.instrument_code,
                             )

        modified_order = copy(existing_order)
        modify_status = modified_order.reject_modification()
        if modify_status is not success:
            log("Can't reject a modification unless an order is being modified but hasn't finished %d" % order_id)
            return failure

        result = self._change_order_on_stack(existing_order.order_id, modified_order,
                                             check_if_orders_being_modified=False)

        return result


    def clear_modification_of_order_on_stack(self, order_id):
        """
        Make a change of quantity to an order on the stack
        This is a 3 phase process
        This is phase three. We can do this once all the orders in our family are completed

        :param order_id:
        :return:
        """

        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn("Can't modify non existent order %d" % order_id)
            return missing_order

        log = self.log.setup(strategy_name=existing_order.strategy_name,
                             instrument_code=existing_order.instrument_code,
                             instrument_order_id = order_id)

        modified_order = copy(existing_order)
        modify_status = modified_order.clear_modification()
        if modify_status is not success:
            log("Need to complete modification of order %d before clearing modification" % order_id)
            return failure

        result = self._change_order_on_stack(existing_order.order_id, modified_order,
                                             check_if_orders_being_modified=False)

        return result


    # FILLS
    def change_fill_quantity_for_order(self, order_id, fill_qty, filled_price = None, fill_datetime=None):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn("Can't apply fill to non existent order %d" % order_id)
            return missing_order

        log = self.log.setup(strategy_name=existing_order.strategy_name,
                             instrument_code=existing_order.instrument_code,
                             instrument_order_id = order_id)

        new_order = copy(existing_order)
        try:
            new_order.fill_order(fill_qty, filled_price=filled_price, fill_datetime=fill_datetime)
        except Exception as e:
            log.warn(e)
            return failure

        result = self._change_order_on_stack(order_id, new_order, check_if_orders_being_modified=False)

        log.msg("Changed fill qty from %s to %s for order %s" % (str(existing_order.fill), str(fill_qty), str(existing_order)))

        return result


    # DEACTIVATE ORDER (Because filled or cancelled)

    def deactivate_order(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn("Can't deactivate non existent order" % order_id)
            return missing_order

        log = self.log.setup(strategy_name=existing_order.strategy_name,
                             instrument_code=existing_order.instrument_code,
                             instrument_order_id = order_id)

        if not existing_order.active:
            # already inactive
            return failure

        new_order = copy(existing_order)
        new_order.deactivate()

        # This will fail if being modified or locked
        result = self._change_order_on_stack(order_id, new_order, check_if_inactive=False)

        return result


    # REMOVE DEACTIVATED ORDERS (SPRING CLEANING - SHOULD BE ARCHIVED)

    def remove_all_deactivated_orders_from_stack(self):
        inactive_orders = self.get_list_of_inactive_order_ids()
        for order_id in inactive_orders:
            self.remove_order_with_id_from_stack(order_id)

        return success

    def get_list_of_inactive_order_ids(self):
        all_order_ids = self._get_list_of_all_order_ids()
        all_orders = [self.get_order_with_id_from_stack(order_id) for order_id in all_order_ids]
        order_ids = [order.order_id for order in all_orders if not order.active]

        return order_ids


    def remove_order_with_id_from_stack(self, order_id):
        order_on_stack = self.get_order_with_id_from_stack(order_id)
        if order_on_stack is missing_order:
            raise Exception("Can't remove non existent order %s from stack" % order_id)
        if order_on_stack.is_order_locked():
            raise Exception("Can't remove locked order %s from stack" % order_on_stack)
        if order_on_stack.active:
            raise Exception("Can't remove active order %s from stack" % order_on_stack)

        self._remove_order_with_id_from_stack_no_checking(order_id)

        return success


    # CHANGING AN ORDER ON THE STACK

    def _change_order_on_stack(self, order_id, new_order, check_if_orders_being_modified=True,
                               check_if_inactive = True):
        # Make any kind of general change to an order, checking for locks
        # Doesn't check for other conditions, eg beingactive or not

        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            self.log.warn("Can't change non existent order %d" % order_id, instrument_order_id = order_id)
            return missing_order

        log = self.log.setup(strategy_name=existing_order.strategy_name,
                             instrument_code=existing_order.instrument_code,
                             instrument_order_id = order_id)

        lock_status = existing_order.is_order_locked()
        if lock_status is True:
            # already locked can't change
            log.warn("Can't change locked order %s" % str(existing_order))
            return locked_order

        if check_if_orders_being_modified:
            if existing_order.is_order_in_modification_states():
                log.warn("Can't change order %s as being modified" % str(existing_order))
                return order_is_in_status_modified

        if check_if_inactive:
            if not existing_order.active:
                log.warn("Can't change order %s as inactive" % str(existing_order))

        try:
            self._lock_order_on_stack(order_id)
            result = self._change_order_on_stack_no_checking(order_id, new_order)
        finally:
            self._unlock_order_on_stack(order_id)

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
        # We only zero order trades if they are modifying an existing trade, otherwise pointless

        if order.order_id is no_order_id:
            pass
        else:
            self.log.warn("Order %s already has order ID will be ignored" % str(order))
        order_to_add = copy(order)
        order_id = self._get_next_order_id()
        order_to_add.order_id= order_id

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

    ## ORDER ID

    def _get_next_order_id(self):
        ## MUST override in data implementation
        ## The maximum orderid should ideally live on in permanent storage
        ## Otherwise we rely on this stack persisting while downstream stacks rely on mapping orderids

        order_id_on_stack = self.get_list_of_order_ids()
        if len(order_id_on_stack)==0:
            return 1

        max_order_id_on_stack = max(order_id_on_stack)

        return max_order_id_on_stack+1


    # FINDING ORDERS AND LIST OF ORDERS

    def _get_order_with_same_tradeable_object_on_stack(self, order):
        """
        Try and get an order with the same tradeable object off the stack

        :param order: Order to check
        :return: Existing order or missing_order or identical_order
        """
        order_key = order.key
        existing_order = self.get_order_with_key_from_stack(order_key)
        if existing_order is missing_order:
            return missing_order
        are_orders_equal = order==existing_order
        if are_orders_equal:
            return duplicate_order

        return existing_order

    def _get_list_of_orders_with_key_from_stack(self, order_key,   exclude_inactive_orders = True):

        all_order_ids = self.get_list_of_order_ids(exclude_inactive_orders = exclude_inactive_orders)
        all_orders = [self.get_order_with_id_from_stack(order_id) for order_id in all_order_ids]
        order_ids = [order.order_id for order in all_orders if order.key == order_key]

        return order_ids

    def _get_list_of_all_order_ids(self):
        # probably will be overriden in data implementation
        return list(self._stack.keys())

    # deleting

    def _remove_order_with_id_from_stack_no_checking(self, order_id):
        # probably will be overriden in data implementation

        self._stack.pop(order_id)


    def _delete_entire_stack_without_checking(self):
        # probably will be overriden in data implementation
        self._stack = {}
        return success

