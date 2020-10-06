from copy import copy
import datetime
import numpy as np
import pandas as pd

from syscore.genutils import are_dicts_equal, none_to_object, object_to_none, sign
from syscore.objects import success, no_order_id, no_children, no_parent, missing_order
from syscore.genutils import sign


class tradeableObject(object):
    """
    Could be an instrument, or contract. This is the base class
    """

    def __init__(self, object_name):
        # probably overriden with nicer entry
        obj_def_dict = dict(object_name=object_name)
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
        return self._definition["object_name"]


class tradeQuantity(object):
    def __init__(self, trade_or_fill_qty):
        if isinstance(trade_or_fill_qty, tradeQuantity):
            trade_or_fill_qty = trade_or_fill_qty.qty

        elif (isinstance(trade_or_fill_qty, float)) or (isinstance(trade_or_fill_qty, int)):
            trade_or_fill_qty = [trade_or_fill_qty]
            # must be a list
            assert isinstance(trade_or_fill_qty, list)

        self._trade_or_fill_qty = trade_or_fill_qty

    def __repr__(self):
        return str(self.qty)

    @property
    def qty(self):
        return self._trade_or_fill_qty

    def zero_version(self):
        len_self = len(self.qty)
        return tradeQuantity([0] * len_self)

    def fill_less_than_or_equal_to_desired_trade(self, proposed_fill):
        return all(
            [
                abs(x) <= abs(y) and x * y >= 0
                for x, y in zip(proposed_fill.qty, self.qty)
            ]
        )

    def equals_zero(self):
        return all([x == 0 for x in self.qty])

    def sign_equal(self, other):
        return all([sign(x) == sign(y) for x, y in zip(self.qty, other.qty)])

    def __len__(self):
        return len(self.qty)

    def __eq__(self, other):
        return all([x == y for x, y in zip(self.qty, other.qty)])

    def __sub__(self, other):
        assert len(self.qty) == len(other.qty)
        result = [x - y for x, y in zip(self.qty, other.qty)]
        result = tradeQuantity(result)
        return result

    def __add__(self, other):
        assert len(self.qty) == len(other.qty)
        result = [x + y for x, y in zip(self.qty, other.qty)]
        result = tradeQuantity(result)
        return result

    def __radd__(self, other):
        if other == 0:
            return self
        else:
            return self.__add__(other)

    def __getitem__(self, item):
        return self._trade_or_fill_qty[item]

    def total_abs_qty(self):
        abs_qty_list = [abs(x) for x in self.qty]
        return sum(abs_qty_list)

    def change_trade_size_proportionally(self, new_trade):
        current_abs_qty = self.total_abs_qty()
        new_abs_qty = float(new_trade)
        ratio = new_abs_qty / current_abs_qty
        new_qty = [int(np.floor(ratio * qty)) for qty in self.qty]
        self._trade_or_fill_qty = new_qty

    def sort_with_idx(self, idx_list):
        unsorted = self.qty
        qty_sorted = [unsorted[idx] for idx in idx_list]
        self._trade_or_fill_qty = qty_sorted

    def as_int(self):
        if len(self._trade_or_fill_qty) > 1:
            return missing_order
        return self._trade_or_fill_qty[0]

    def apply_minima(self, abs_list):
        # for each item in _trade and abs_list, return the signed minimum of the zip
        # eg if self._trade = [2,-2] and abs_list = [1,1], return [2,-2]
        applied_list = apply_minima(self._trade_or_fill_qty, abs_list)

        return tradeQuantity(applied_list)

    def apply_min_size(self, min_size):
        """
        Cut the trade down proportionally so the smallest leg is min_size
        eg self = [2], min_size = 1 -> [1]
        self = [-2,2], min_size = 1 -> [-1,1]
        self = [-2,4,-2], min_size = 1 -> [-1,2,2]
        self = [-3,4,-3], min_size = 1 -> [-3,4,-3]

        :param min_size:
        :return: tradeQuantity
        """

        new_trade_list = apply_min_size(self._trade_or_fill_qty, min_size)
        return tradeQuantity(new_trade_list)

    def get_spread_price(self, list_of_prices):
        if list_of_prices is None:
            return None
        if isinstance(
                list_of_prices,
                int) or isinstance(
                list_of_prices,
                float):
            list_of_prices = [list_of_prices]

        assert len(self._trade_or_fill_qty) == len(list_of_prices)

        if len(self._trade_or_fill_qty) == 1:
            return list_of_prices[0]

        # spread price won't make sense otherwise
        assert sum(self._trade_or_fill_qty) == 0

        sign_to_adjust = sign(self._trade_or_fill_qty[0])
        multiplied_prices = [
            x * y * sign_to_adjust
            for x, y in zip(self._trade_or_fill_qty, list_of_prices)
        ]

        return sum(multiplied_prices)

    def buy_or_sell(self):
        return sign(self.qty[0])


def apply_minima(trade_list, abs_list):
    # for each item in _trade and abs_list, return the signed minimum of the zip
    # eg if self._trade = [2,-2] and abs_list = [1,1], return [2,-2]
    abs_trade_list = [abs(x) for x in trade_list]
    smallest_abs_leg = min(abs_trade_list)
    if smallest_abs_leg == 0:
        # can't do this
        return trade_list

    abs_size_ratio_list = [
        min([x, y]) / float(x) for x, y in zip(abs_trade_list, abs_list)
    ]
    min_abs_size_ratio = min(abs_size_ratio_list)
    new_smallest_leg = np.floor(smallest_abs_leg * min_abs_size_ratio)
    ratio_applied = new_smallest_leg / smallest_abs_leg
    trade_list_with_ratio_as_float = [x * ratio_applied for x in trade_list]
    trade_list_with_ratio_as_int = [int(x)
                                    for x in trade_list_with_ratio_as_float]
    diff = [
        abs(x - y)
        for x, y in zip(trade_list_with_ratio_as_float, trade_list_with_ratio_as_int)
    ]
    largediff = any([x > 0.0001 for x in diff])
    if largediff:
        trade_list_with_ratio_as_int = [0] * len(trade_list)

    return trade_list_with_ratio_as_int


def apply_min_size(trade_list, min_size):
    """
    Cut the trade down proportionally so the smallest leg is min_size
    eg self = [2], min_size = 1 -> [1]
    self = [-2,2], min_size = 1 -> [-1,1]
    self = [-2,4,-2], min_size = 1 -> [-1,2,2]
    self = [-3,4,-3], min_size = 1 -> [-3,4,-3]

    :param min_size:
    :return: tradeQuantity
    """
    abs_trade_list = [abs(x) for x in trade_list]
    smallest_abs_leg = min(abs_trade_list)
    new_smallest_leg = min_size
    ratio_applied = new_smallest_leg / smallest_abs_leg
    trade_list_with_ratio_as_float = [x * ratio_applied for x in trade_list]
    trade_list_with_ratio_as_int = [int(x)
                                    for x in trade_list_with_ratio_as_float]
    diff = [
        abs(x - y)
        for x, y in zip(trade_list_with_ratio_as_float, trade_list_with_ratio_as_int)
    ]
    largediff = any([x > 0.0001 for x in diff])
    if largediff:
        return trade_list

    return trade_list_with_ratio_as_int


def adjust_spread_order_single_benchmark(order, benchmark_list, actual_price):

    spread_price_from_benchmark = order.trade.get_spread_price(benchmark_list)
    adjustment_to_benchmark = actual_price - spread_price_from_benchmark
    adjusted_benchmark_prices = [
        price + adjustment_to_benchmark for price in benchmark_list
    ]

    return adjusted_benchmark_prices


class fillPrice(object):
    def __init__(self, fill_price):
        if isinstance(fill_price, fillPrice):
            fill_price = fill_price.price
        if (isinstance(fill_price, float)) or (isinstance(fill_price, int)):
            fill_price = [fill_price]
        # must be a list
        assert isinstance(fill_price, list)

        self._price = fill_price

    def __repr__(self):
        return str(self.price)

    @property
    def price(self):
        return self._price

    @classmethod
    def nan_from_trade_qty(fillPrice, trade_qty):
        len_self = len(trade_qty.qty)
        return fillPrice([np.nan] * len_self)

    def sort_with_idx(self, idx_list):
        unsorted = self.price
        price_sorted = [unsorted[idx] for idx in idx_list]
        self._price = price_sorted

    def __getitem__(self, item):
        return self._price[item]

    def __len__(self):
        return len(self.price)


class listOfFillPrice(list):
    def average_fill_price(self):
        len_items = len(self[0])  # assume all the same length
        averages = [self._average_for_item(idx) for idx in range(len_items)]
        return fillPrice(averages)

    def _average_for_item(self, idx):
        prices_for_item = [element.price[idx] for element in self]
        prices_for_item = [
            price for price in prices_for_item if not np.isnan(price)]
        return np.mean(prices_for_item)


class listOfFillDatetime(list):
    def final_fill_datetime(self):
        valid_dates = [dt for dt in self if dt is not None]

        return max(valid_dates)


def resolve_trade_fill_fillprice(trade, fill, filled_price):
    resolved_trade = tradeQuantity(trade)
    if fill is None:
        resolved_fill = resolved_trade.zero_version()
    else:
        resolved_fill = tradeQuantity(fill)

    if filled_price is None:
        resolved_filled_price = fillPrice.nan_from_trade_qty(resolved_trade)
    else:
        resolved_filled_price = fillPrice(filled_price)

    return resolved_trade, resolved_fill, resolved_filled_price


class Order(object):
    """
    An order represents a desired or completed trade
    This is a base class, specific orders are used for virtual and contract level orders

    Need to be able to compare orders with each other to enforce the 'no multiple orders of same characteristics'
    """

    def __init__(
        self,
        object_name,
        trade,
        fill=None,
        filled_price=None,
        fill_datetime=None,
        locked=False,
        order_id=no_order_id,
        modification_status=None,
        modification_quantity=None,
        parent=no_parent,
        children=no_children,
        active=True,
        **kwargs
    ):
        """

        :param object_name: name for a tradeableObject, str
        :param trade: trade we want to do, int or list
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

        (
            resolved_trade,
            resolved_fill,
            resolved_filled_price,
        ) = resolve_trade_fill_fillprice(trade, fill, filled_price)

        if children == []:
            children = no_children

        self._trade = resolved_trade
        self._fill = resolved_fill
        self._filled_price = resolved_filled_price
        self._fill_datetime = fill_datetime
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
            lock_str = "LOCKED"
        else:
            lock_str = ""
        if not self._active:
            active_str = "INACTIVE"
        else:
            active_str = ""
        return "(Order ID:%s) For %s, qty %s fill %s,  Parent:%s Child:%s %s %s" % (
            str(self.order_id),
            str(self.key),
            str(self.trade),
            str(self.fill),
            str(self._parent),
            str(self._children),
            lock_str,
            active_str,
        )

    @property
    def trade(self):
        return tradeQuantity(self._trade)

    def replace_trade_only_use_for_unsubmitted_trades(self, new_trade):
        # if this is a single leg trade, does a straight replacement
        # otherwise

        new_order = copy(self)
        new_order._trade = tradeQuantity(new_trade)

        return new_order

    def change_trade_size_proportionally(self, new_trade):
        # if this is a single leg trade, does a straight replacement
        # otherwise

        new_order = copy(self)
        new_order._trade.change_trade_size_proportionally(new_trade)

        return new_order

    @property
    def fill(self):
        return tradeQuantity(self._fill)

    @property
    def filled_price(self):
        return fillPrice(self._filled_price)

    @property
    def fill_datetime(self):
        return self._fill_datetime

    def fill_order(self, fill_qty, filled_price=None, fill_datetime=None):
        # Fill qty is cumulative, eg this is the new amount filled
        fill_qty = tradeQuantity(fill_qty)

        assert self.trade.fill_less_than_or_equal_to_desired_trade(
            fill_qty
        ), "Can't fill order for more than trade quantity"

        self._fill = fill_qty
        if filled_price is not None:
            self._filled_price = fillPrice(filled_price)

        if fill_datetime is None:
            fill_datetime = datetime.datetime.now()

        self._fill_datetime = fill_datetime

    def fill_equals_zero(self):
        return self.fill.equals_zero()

    def fill_equals_desired_trade(self):
        return self.fill == self.trade

    def is_zero_trade(self):
        return self.trade.equals_zero()

    @property
    def order_id(self):
        return self._order_id

    @order_id.setter
    def order_id(self, order_id):
        assert isinstance(order_id, int)
        current_id = getattr(self, "_order_id", no_order_id)
        if current_id is no_order_id:
            self._order_id = order_id
        else:
            raise Exception("Can't change order id once set")

    @property
    def children(self):
        return self._children

    @children.setter
    def children(self, children):
        if isinstance(children, int):
            children = [children]
        if self._children == no_children:
            self._children = children
        else:
            raise Exception(
                "Can't add children to order which already has them: use add another child"
            )

    def remove_children(self):
        self._children = no_children

    def add_another_child(self, new_child):
        if self.children is no_children:
            new_children = [new_child]
        else:
            new_children = self.children + [new_child]

        self._children = new_children

    @property
    def remaining(self):
        return self.trade - self.fill

    def order_with_remaining(self):
        new_order = copy(self)
        new_trade = self.remaining
        new_order._trade = new_trade
        new_order._fill = new_trade.zero_version()
        new_order._filled_price = fillPrice.nan_from_trade_qty(new_trade)
        new_order._fill_datetime = None

        return new_order

    def order_with_min_size(self, min_size):
        new_order = copy(self)
        new_trade = new_order.trade.apply_min_size(min_size)
        new_order._trade = new_trade

        return new_order

    def set_trade_to_fill(self):
        self._trade = self._fill

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        if self._parent == no_parent:
            self._parent = parent
        else:
            raise Exception("Can't add parent to order which already has them")

    @property
    def active(self):
        return self._active

    def deactivate(self):
        # Once deactivated: filled or cancelled, we can never go back!
        self._active = False

    def zero_out(self):
        zero_version = self.trade.zero_version()
        self._fill = zero_version
        self.deactivate()

    def as_dict(self):
        object_dict = dict(key=self.key)
        object_dict["trade"] = self.trade.qty
        object_dict["fill"] = self.fill.qty
        object_dict["fill_datetime"] = self.fill_datetime
        object_dict["filled_price"] = self.filled_price.price
        object_dict["locked"] = self._locked
        object_dict["order_id"] = object_to_none(self.order_id, no_order_id)
        object_dict["modification_status"] = self._modification_status
        object_dict["modification_quantity"] = self._modification_quantity
        object_dict["parent"] = object_to_none(self.parent, no_parent)
        object_dict["children"] = object_to_none(self.children, no_children)
        object_dict["active"] = self.active
        for info_key, info_value in self._order_info.items():
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
        order_id = none_to_object(order_as_dict.pop("order_id"), no_order_id)
        modification_status = order_as_dict.pop("modification_status")
        modification_quantity = order_as_dict.pop("modification_quantity")
        parent = none_to_object(order_as_dict.pop("parent"), no_parent)
        children = none_to_object(order_as_dict.pop("children"), no_children)
        active = order_as_dict.pop("active")

        order_info = order_as_dict

        order = Order(
            object_name,
            trade,
            fill=fill,
            fill_datetime=fill_datetime,
            filled_price=filled_price,
            locked=locked,
            order_id=order_id,
            modification_status=modification_status,
            modification_quantity=modification_quantity,
            parent=parent,
            children=children,
            active=active,
            **order_info
        )

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


class listOfOrders(list):
    def as_pd(self):
        date_list = [order.fill_datetime for order in self]
        key_list = [order.key for order in self]
        fill_list = [order.fill for order in self]
        id_list = [order.order_id for order in self]
        price_list = [order.filled_price for order in self]

        pd_df = pd.DataFrame(
            dict(
                fill_datetime=date_list,
                key=key_list,
                fill=fill_list,
                price=price_list),
            index=id_list,
        )

        return pd_df
