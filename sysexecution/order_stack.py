from syscore.genutils import are_dicts_equal
from syscore.objects import missing_order, success, failure, locked_order, duplicate_order


class tradeableObject(dict):
    """
    Could be an instrument, or contract. This is the base class
    """

    def __init__(self, object_name):
        # probably overriden with nicer entry
        obj_def_dict = dict(object_name = object_name)
        self._set_definition(obj_def_dict)

    def _set_definition(self, obj_def_dict):
        self._definition = obj_def_dict

    def __repr__(self):
        return self.key

    @classmethod
    def from_key(tradeableObject, object_name):
        return tradeableObject(object_name)

    def __eq__(self, other):
        return are_dicts_equal(self._definition, other._definition)

    @property
    def key(self):
        # probably overriden
        return self._definition['object_name']

class Order(object):
    """
    An order represents a desired or completed trade
    This is a base class, specific orders are used for virtual and contract level orders

    Need to be able to compare orders with each other to enforce the 'no multiple orders of same characteristics'
    """


    def __init__(self, object_name, trade: int, locked=False, **kwargs):
        self._tradeable_object = tradeableObject(object_name)

        self.trade = trade
        self._locked = locked
        self.order_info = kwargs

    def __repr__(self):
        return "Order %s %f" % (str(self.key), self.trade)

    def as_dict(self):
        object_dict = dict(key = self.key)
        object_dict['trade'] = self.trade
        object_dict['locked'] = self._locked
        for info_key, info_value in self.order_info.items():
            object_dict[info_key] = info_value

        return object_dict



    @classmethod
    def from_dict(Order, order_as_dict):
        ## will need modifying in child classes
        trade = order_as_dict.pop('trade')
        object_name = order_as_dict.pop('key')
        locked = order_as_dict.pop('locked')
        order_info = order_as_dict

        order = Order(object_name, trade, locked = locked, **order_info)

        return order

    @property
    def key(self):
        return self._tradeable_object.key

    def is_order_locked(self):
        return self._locked

    def lock_order(self):
        self._locked = True

    def unlock_order(self):
        self._locked = False

    def same_tradeable_object(self, other):
        my_object = self._tradeable_object
        other_object = other._tradeable_object
        return my_object == other_object

    def same_trade_size(self, other):
        my_trade = self.trade
        other_trade = other.trade

        return my_trade == other_trade

    def __eq__(self, other):
        same_def = self.same_tradeable_object(other)
        same_trade = self.same_trade_size(other)

        return same_def and same_trade

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

    def __init__(self):
        self._stack = dict()

    def __repr__(self):
        return "Order stack: %s" % str(self._stack)

    def put_order_on_stack(self, new_order):
        """
        Put an order on the stack, or at least try to:
        - if no existing order, add
        - if an existing order exists:
            - and locked, don't allow
            - if unlocked:
                 - order is identical, do nothing
                 - order is not identical, update

        :param new_order: Order
        :return: success or failure
        """

        existing_order = self._get_order_with_same_tradeable_object_on_stack(new_order)
        if existing_order is duplicate_order:
            # Do nothing, pointless
            return duplicate_order

        if existing_order is missing_order:
            # No existing order
            result = self._put_order_on_stack_no_checking(new_order)
            return result

        # Check for lock
        order_locked = existing_order.is_order_locked()
        if order_locked:
            # Do nothing
            return locked_order

        # Existing order needs modifying
        result = self._modify_order_on_stack_no_checking(new_order)

        return result

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


    def unlock_order_on_stack(self, order_key):
        order = self.get_order_with_key_from_stack(order_key)
        if order is missing_order:
            return failure
        order.unlock_order()
        self._modify_order_on_stack_no_checking(order)
        return success

    def lock_order_on_stack(self, order_key):
        order = self.get_order_with_key_from_stack(order_key)
        if order is missing_order:
            return failure
        order.lock_order()
        self._modify_order_on_stack_no_checking(order)
        return success

    def _put_order_on_stack_no_checking(self, order):
        # probably will be overriden in data implementation

        order_key = order.key
        self._stack[order_key] = order
        return success

    def _modify_order_on_stack_no_checking(self, order):
        # probably will be overriden in data implementation

        order_key = order.key
        self._stack[order_key] = order
        return success

    def clear_order_with_key_from_stack(self, order_key):
        # unlocks and removes - use with care!
        self.unlock_order_on_stack(order_key)

        return self.remove_order_with_key_from_stack(order_key)

    def remove_order_with_key_from_stack(self, order_key):
        order_on_stack = self.get_order_with_key_from_stack(order_key)
        if order_on_stack is missing_order:
            raise Exception("Can't remove non existent order %s from stack" % order_key)
        if order_on_stack.is_order_locked():
            raise Exception("Can't remove locked order %s from stack" % order_on_stack)

        self._remove_order_with_key_from_stack_no_checking(order_key)

        return success

    def get_order_with_key_from_stack(self, order_key):
        # probably will be overriden in data implementation

        order = self._stack.get(order_key, missing_order)
        return order

    def _remove_order_with_key_from_stack_no_checking(self, order_key):
        # probably will be overriden in data implementation

        self._stack.pop(order_key)

    def get_list_of_order_keys(self):
        # probably will be overriden in data implementation
        return list(self._stack.keys())

    def get_order_for_execution_from_stack(self, order_key):
        order = self.get_order_with_key_from_stack(order_key)
        if order is missing_order:
            return missing_order

        self.lock_order_on_stack(order_key)

        return order

    def empty_stack(self, are_you_sure=False):
        if are_you_sure:
            return self._empty_stack_without_checking()
        else:
            return failure

    def _empty_stack_without_checking(self):
        # probably will be overriden in data implementation
        self._stack = {}
        return success