import numpy as np
from copy import copy
import datetime

from syscore.genutils import (
    if_empty_string_return_object,
    if_object_matches_return_empty_string,
    list_of_ints_with_highest_common_factor_positive_first,
)
from sysexecution.orders.named_order_objects import no_order_id, no_children, no_parent

from sysexecution.trade_qty import tradeQuantity

from sysobjects.production.tradeable_object import tradeableObject


class overFilledOrder(Exception):
    pass


class orderType(object):
    def __repr__(self):
        return self.as_string()

    def allowed_types(self):
        return ["market"]

    def __init__(self, type_string: str):
        if type_string is None:
            type_string = ""
        else:
            assert type_string in self.allowed_types(), (
                "Type %s not valid" % type_string
            )

        self._type = type_string

    def as_string(self):
        return self._type

    def __eq__(self, other):
        return self.as_string() == other.as_string()


class Order(object):
    """
    An order represents a desired or completed trade
    This is a base class, specific orders are used for virtual and contract level orders

    Need to be able to compare orders with each other to enforce the 'no multiple orders of same characteristics'
    """

    def __init__(
        self,
        tradeable_object: tradeableObject,
        trade: tradeQuantity,
        fill: tradeQuantity = None,
        filled_price: float = None,
        fill_datetime: datetime.datetime = None,
        locked=False,
        order_id: int = no_order_id,
        parent: int = no_parent,
        children: list = no_children,
        active: bool = True,
        order_type: orderType = orderType("market"),
        **order_info,
    ):
        """

        :param object_name: name for a tradeableObject, str
        :param trade: trade we want to do, int or list
        :param fill: fill done so far, int
        :param fill_datetime: when fill done (if multiple, is last one)
        :param fill_price: price of fill (if multiple, is last one)
        :param locked: if locked an order can't be modified, bool
        :param order_id: ID given to orders once in the stack, do not use when creating order
        :param parent: int, order ID of parent order in upward stack
        :param children: list of int, order IDs of child orders in downward stack
        :param active: bool, inactive orders have been filled or cancelled
        :param kwargs: other interesting arguments
        """
        self._tradeable_object = tradeable_object

        (
            resolved_trade,
            resolved_fill,
        ) = resolve_inputs_to_order(trade, fill)

        if children == []:
            children = no_children

        self._trade = resolved_trade
        self._fill = resolved_fill
        self._filled_price = filled_price
        self._fill_datetime = fill_datetime
        self._locked = locked
        self._order_id = order_id
        self._parent = parent
        self._children = children
        self._active = active
        self._order_type = order_type
        self._order_info = order_info

    def __repr__(self):
        terse_repr = self.terse_repr()

        return terse_repr

    def full_repr(self):
        terse_repr = self.terse_repr()
        full_repr = terse_repr + " %s" % str(self._order_info)

        return full_repr

    def terse_repr(self):
        if self._locked:
            lock_str = " LOCKED"
        else:
            lock_str = ""
        if not self._active:
            active_str = " INACTIVE"
        else:
            active_str = ""
        return (
            "(Order ID:%s) Type %s for %s, qty %s, fill %s@ price, %s Parent:%s Children:%s%s%s"
            % (
                str(self.order_id),
                str(self._order_type),
                str(self.key),
                str(self.trade),
                str(self.fill),
                str(self.filled_price),
                str(self.parent),
                str(self.children),
                lock_str,
                active_str,
            )
        )

    @property
    def order_info(self):
        return self._order_info

    @property
    def tradeable_object(self):
        return self._tradeable_object

    @property
    def trade(self):
        return self._trade

    def sign_of_single_trade(self):
        return self.trade.sign_of_single_trade()

    def as_single_trade_qty_or_error(self) -> int:
        return self.trade.as_single_trade_qty_or_error()

    def replace_required_trade_size_only_use_for_unsubmitted_trades(
        self, new_trade: tradeQuantity
    ):

        # ensure refactoring works
        assert type(new_trade) is tradeQuantity

        try:
            assert len(new_trade) == len(self.trade)
        except:
            raise Exception(
                "Trying to replace trade of length %d with one of length %d"
                % (len(self.trade), len(new_trade))
            )

        new_order = copy(self)
        new_order._trade = new_trade

        return new_order

    @property
    def order_type(self):
        return self._order_type

    @order_type.setter
    def order_type(self, order_type: orderType):
        self._order_type = order_type

    @property
    def fill(self):
        return tradeQuantity(self._fill)

    @property
    def filled_price(self):
        return self._filled_price

    @property
    def fill_datetime(self):
        return self._fill_datetime

    def fill_order(
        self,
        fill_qty: tradeQuantity,
        filled_price: float,
        fill_datetime: datetime.datetime = None,
    ):
        # Fill qty is cumulative, eg this is the new amount filled
        try:
            assert self.trade.fill_less_than_or_equal_to_desired_trade(fill_qty)
        except:
            raise overFilledOrder(
                "Can't fill order with fill %s more than trade quantity %s "
                % (str(fill_qty), str(self.trade))
            )

        self._fill = fill_qty
        self._filled_price = filled_price

        if fill_datetime is None:
            fill_datetime = datetime.datetime.now()

        self._fill_datetime = fill_datetime

    def fill_equals_zero(self) -> bool:
        return self.fill.equals_zero()

    def fill_equals_desired_trade(self) -> bool:
        return self.fill == self.trade

    def is_zero_trade(self) -> bool:
        return self.trade.equals_zero()

    @property
    def order_id(self) -> int:
        order_id = resolve_orderid(self._order_id)
        return order_id

    @order_id.setter
    def order_id(self, order_id: int):
        assert isinstance(order_id, int)
        current_id = getattr(self, "_order_id", no_order_id)
        if current_id is no_order_id:
            self._order_id = order_id
        else:
            raise Exception("Can't change order id once set")

    @property
    def children(self) -> list:
        return self._children

    @children.setter
    def children(self, children):
        if isinstance(children, int):
            children = [children]

        if not self.no_children():
            raise Exception(
                "Can't add children to order which already has them: use add another child"
            )

        self._children = children

    def remove_all_children(self):
        self._children = no_children

    def no_children(self):
        return self.children is no_children

    def add_a_list_of_children(self, list_of_new_children: list):
        _ = [self.add_another_child(new_child) for new_child in list_of_new_children]

    def add_another_child(self, new_child: int):
        if self.no_children():
            new_children = [new_child]
        else:
            new_children = self.children + [new_child]

        self._children = new_children

    @property
    def remaining(self) -> tradeQuantity:
        return self.trade - self.fill

    def create_order_with_unfilled_qty(self):
        new_order = copy(self)
        new_trade = self.remaining
        new_order._trade = new_trade
        new_order._fill = new_trade.zero_version()
        new_order._filled_price = None
        new_order._fill_datetime = None

        return new_order

    def change_trade_size_proportionally_to_meet_abs_qty_limit(self, max_abs_qty: int):
        # if this is a single leg trade, does a straight replacement
        # otherwise

        new_order = copy(self)
        old_trade = new_order.trade
        new_trade = old_trade.change_trade_size_proportionally_to_meet_abs_qty_limit(
            max_abs_qty
        )
        new_order = (
            new_order.replace_required_trade_size_only_use_for_unsubmitted_trades(
                new_trade
            )
        )

        return new_order

    def reduce_trade_size_proportionally_so_smallest_leg_is_max_size(
        self, max_size: int
    ):

        new_order = copy(self)
        old_trade = new_order.trade
        new_trade = (
            old_trade.reduce_trade_size_proportionally_so_smallest_leg_is_max_size(
                max_size
            )
        )
        new_order = (
            new_order.replace_required_trade_size_only_use_for_unsubmitted_trades(
                new_trade
            )
        )

        return new_order

    def change_trade_qty_to_filled_qty(self):
        self._trade = self._fill

    @property
    def parent(self):
        parent = resolve_parent(self._parent)
        return parent

    @parent.setter
    def parent(self, parent: int):
        if self._parent == no_parent:
            self._parent = int(parent)
        else:
            raise Exception("Can't add parent to order which already has them")

    @property
    def active(self):
        return bool(self._active)

    def deactivate(self):
        # Once deactivated: filled or cancelled, we can never go back!
        self._active = False

    def zero_out(self):
        zero_version_of_trades = self.trade.zero_version()
        self._fill = zero_version_of_trades
        self.deactivate()

    def as_dict(self):
        object_dict = dict(key=self.key)
        object_dict["trade"] = list(self.trade)
        object_dict["fill"] = list(self.fill)
        object_dict["fill_datetime"] = self.fill_datetime
        object_dict["filled_price"] = self.filled_price
        object_dict["locked"] = self._locked
        object_dict["order_id"] = if_object_matches_return_empty_string(
            self.order_id, no_order_id
        )
        object_dict["parent"] = if_object_matches_return_empty_string(
            self.parent, no_parent
        )
        object_dict["children"] = if_object_matches_return_empty_string(
            self.children, no_children
        )
        object_dict["active"] = self.active
        object_dict["order_type"] = self.order_type.as_string()
        for info_key, info_value in self.order_info.items():
            object_dict[info_key] = info_value

        return object_dict

    @classmethod
    def from_dict(Order, order_as_dict):
        # will need modifying in child classes
        trade = order_as_dict.pop("trade")
        object_name = order_as_dict.pop("key")
        locked = order_as_dict.pop("locked")
        fill = order_as_dict.pop("fill")
        filled_price = order_as_dict.pop("filled_price")
        fill_datetime = order_as_dict.pop("fill_datetime")
        order_id = if_empty_string_return_object(
            order_as_dict.pop("order_id"), no_order_id
        )
        parent = if_empty_string_return_object(order_as_dict.pop("parent"), no_parent)
        children = if_empty_string_return_object(
            order_as_dict.pop("children"), no_children
        )
        active = order_as_dict.pop("active")
        order_type = orderType(order_as_dict.pop("order_type", None))

        order_info = order_as_dict

        order = Order(
            object_name,
            trade,
            fill=fill,
            fill_datetime=fill_datetime,
            filled_price=filled_price,
            locked=locked,
            order_id=order_id,
            parent=parent,
            children=children,
            active=active,
            order_type=order_type,
            **order_info,
        )

        return order

    @property
    def key(self):
        return self.tradeable_object.key

    def is_order_locked(self):
        return bool(self._locked)

    def lock_order(self):
        self._locked = True

    def unlock_order(self):
        self._locked = False

    def same_tradeable_object(self, other):
        my_object = self.tradeable_object
        other_object = other.tradeable_object
        return my_object == other_object

    def same_trade_size(self, other):
        my_trade = self.trade
        other_trade = other.trade

        return my_trade == other_trade

    def __eq__(self, other):
        same_tradeable_object = self.same_tradeable_object(other)
        same_trade = self.same_trade_size(other)

        return same_tradeable_object and same_trade

    def log_with_attributes(self, log):
        """
        Returns a new log object with order attributes added

        :param log: pst_logger
        :return: log
        """

        return log


def resolve_inputs_to_order(trade, fill) -> (tradeQuantity, tradeQuantity):
    resolved_trade = tradeQuantity(trade)
    if fill is None:
        resolved_fill = resolved_trade.zero_version()
    else:
        resolved_fill = tradeQuantity(fill)

    return resolved_trade, resolved_fill


def resolve_orderid(order_id: int):
    if order_id is no_order_id:
        return no_order_id
    if order_id is None:
        return no_order_id
    order_id = int(order_id)
    return order_id


def resolve_parent(parent: int):
    if parent is no_parent:
        return no_parent
    if parent is None:
        return no_parent
    parent = int(parent)

    return parent


def resolve_multi_leg_price_to_single_price(
    trade_list: tradeQuantity, price_list: list
) -> float:

    if len(price_list) == 0:
        ## This will be the case when an order is first created or has no fills
        return None

    if len(price_list) == 1:
        return price_list[0]

    assert len(price_list) == len(trade_list)

    trade_list_as_common_factor = (
        list_of_ints_with_highest_common_factor_positive_first(trade_list)
    )
    fill_price = [x * y for x, y in zip(trade_list_as_common_factor, price_list)]

    fill_price = sum(fill_price)
    if np.isnan(fill_price):
        return None

    return fill_price
