from copy import copy
import datetime
from syscore.genutils import are_dicts_equal, none_to_object, object_to_none
from syscore.objects import  success,  no_order_id, no_children, no_parent


class tradeableObject(object):
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


    def __init__(self, object_name, trade: int, fill=0, filled_price = None, fill_datetime = None,
                 locked=False, order_id=no_order_id,
                 modification_status = None,
                 modification_quantity = None, parent=no_parent,
                 children=no_children, active=True,
                 **kwargs):
        """

        :param object_name: name for a tradeableObject, str
        :param trade: trade we want to do, int
        :param fill: fill done so far, int
        :param fill_datetime: when fill done (if multiple, is last one)
        :param fill_price: price of fill (if multiple, is last one)
        :param locked: if locked an order can't be modified, bool
        :param order_id: ID given to orders once in the stack, do not use when creating order
        :param modification_status: NOT USED
        :param modification_quantity: NOT USED
        :param parent: int, order ID of parent order in upward stack
        :param children: list of int, order IDs of child orders in downward stack
        :param active: bool, inactive orders have been filled or cancelled
        :param kwargs: other interesting arguments
        """
        self._tradeable_object = tradeableObject(object_name)

        self._trade = trade
        self._fill = fill
        self._fill_datetime = fill_datetime
        self._filled_price = filled_price
        self._locked = locked
        self._order_id = order_id
        self._modification_status = modification_status
        self._modification_quantity = modification_quantity
        self._parent = parent
        self._children = children
        self._active = active

        self._order_info = kwargs

    def __repr__(self):
        if self._locked:
            lock_str="LOCKED"
        else:
            lock_str = ""
        if not self._active:
            active_str = "INACTIVE"
        else:
            active_str = ""
        return "(Order ID:%s) For %s, qty %s fill %s,  Parent:%s Child:%s %s %s" % (str(self.order_id), str(self.key), str(self.trade), str(self.fill),
                                          str(self._parent), str(self._children), lock_str, active_str)

    @property
    def trade(self):
        return self._trade

    def replace_trade_only_use_for_unsubmitted_trades(self, new_trade):

        new_order = copy(self)
        new_order._trade = new_trade

        return new_order

    @property
    def fill(self):
        return self._fill

    @property
    def filled_price(self):
        return self._filled_price

    @property
    def fill_datetime(self):
        return self._fill_datetime


    def fill_order(self, fill_qty, filled_price = None, fill_datetime = None):
        # Fill qty is cumulative, eg this is the new amount filled
        assert self.fill_less_than_or_equal_to_desired_trade(fill_qty), "Can't fill order for more than trade quantity"

        self._fill = fill_qty
        if filled_price is not None:
            self._filled_price = filled_price
        if fill_datetime is None:
            fill_datetime = datetime.datetime.now()

        self._fill_datetime = fill_datetime


    def fill_less_than_or_equal_to_desired_trade(self, proposed_fill):
        return abs(proposed_fill) <= abs(self.trade) and (proposed_fill * self.trade) >= 0

    def fill_equals_zero(self):
        return self.fill==0

    def fill_equals_desired_trade(self):
        return self.fill==self.trade

    def is_zero_trade(self):
        return self.trade==0

    @property
    def order_id(self):
        return self._order_id

    @order_id.setter
    def order_id(self, order_id):
        assert type(order_id) is int
        current_id = getattr(self, '_order_id', no_order_id)
        if current_id is no_order_id:
            self._order_id = order_id
        else:
            raise Exception("Can't change order id once set")

    @property
    def children(self):
        return self._children

    @children.setter
    def children(self, children):
        if self._children==no_children:
            self._children = children
        else:
            raise Exception("Can't add children to order which already has them")

    def remove_children(self):
        self._children = no_children

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        if self._parent==no_parent:
            self._parent = parent
        else:
            raise Exception("Can't add parent to order which already has them")

    @property
    def active(self):
        return self._active

    def deactivate(self):
        ## Once deactivated: filled or cancelled, we can never go back!
        self._active = False



    def as_dict(self):
        object_dict = dict(key = self.key)
        object_dict['trade'] = self._trade
        object_dict['fill'] = self._fill
        object_dict['fill_datetime'] = self._fill_datetime
        object_dict['filled_price'] = self._filled_price
        object_dict['locked'] = self._locked
        object_dict['order_id'] = object_to_none(self._order_id, no_order_id)
        object_dict['modification_status'] = self._modification_status
        object_dict['modification_quantity'] = self._modification_quantity
        object_dict['parent'] = object_to_none(self._parent, no_parent)
        object_dict['children'] = object_to_none(self._children, no_children)
        object_dict['active'] = self._active
        for info_key, info_value in self._order_info.items():
            object_dict[info_key] = info_value

        return object_dict

    @classmethod
    def from_dict(Order, order_as_dict):
        ## will need modifying in child classes
        trade = order_as_dict.pop('trade')
        object_name = order_as_dict.pop('key')
        locked = order_as_dict.pop('locked')
        fill = order_as_dict.pop('fill')
        filled_price = order_as_dict.pop('filled_price')
        fill_datetime = order_as_dict.pop('fill_datetime')
        order_id = none_to_object(order_as_dict.pop('order_id'), no_order_id)
        modification_status = order_as_dict.pop('modification_status')
        modification_quantity = order_as_dict.pop('modification_quantity')
        parent = none_to_object(order_as_dict.pop('parent'), no_parent)
        children = none_to_object(order_as_dict.pop('children'), no_children)
        active = order_as_dict.pop('active')

        order_info = order_as_dict

        order = Order(object_name, trade,
                      fill = fill, fill_datetime = fill_datetime, filled_price = filled_price,
                      locked = locked, order_id = order_id,
                      modification_status = modification_status,
                      modification_quantity = modification_quantity,
                      parent = parent, children = children,
                      active = active,
                      **order_info)

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

    def log_with_attributes(self, log):
        """
        Returns a new log object with instrument_order attributes added

        :param log: logger
        :return: log
        """

        raise NotImplementedError
