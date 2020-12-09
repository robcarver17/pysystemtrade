import numpy as np

from syscore.genutils import sign
from syscore.objects import missing_order


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

    def change_trade_size_proportionally_to_meet_abs_qty_limit(self, max_abs_qty):
        new_qty = change_trade_size_proportionally_to_meet_abs_qty_limit(self, max_abs_qty)
        self._trade_or_fill_qty = new_qty

    def sort_with_idx(self, idx_list):
        unsorted = self.qty
        qty_sorted = [unsorted[idx] for idx in idx_list]
        self._trade_or_fill_qty = qty_sorted

    def as_int(self):
        if len(self._trade_or_fill_qty) > 1:
            return missing_order
        return self._trade_or_fill_qty[0]

    def reduce_trade_size_proportionally_to_abs_limit_per_leg(self, abs_list):
        # for each item in _trade and abs_list, return the signed minimum of the zip
        # eg if self._trade = [2,-2] and abs_list = [1,1], return [2,-2]
        applied_list = reduce_trade_size_proportionally_to_abs_limit_per_leg(self._trade_or_fill_qty, abs_list)

        return tradeQuantity(applied_list)

    def reduce_trade_size_proportionally_so_smallest_leg_is_max_size(self, min_size):
        """
        Cut the trade down proportionally so the smallest leg is min_size
        eg self = [2], min_size = 1 -> [1]
        self = [-2,2], min_size = 1 -> [-1,1]
        self = [-2,4,-2], min_size = 1 -> [-1,2,2]
        self = [-3,4,-3], min_size = 1 -> [-3,4,-3]

        :param min_size:
        :return: tradeQuantity
        """

        new_trade_list = reduce_trade_size_proportionally_so_smallest_leg_is_max_size(self._trade_or_fill_qty, min_size)
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


def change_trade_size_proportionally_to_meet_abs_qty_limit(trade_list: tradeQuantity, max_abs_qty: int) -> list:
    """

    :param trade_list: tradeQuantity
    :param max_abs_qty: int
    :return: list of ints


    """
    original_qty = trade_list.qty
    current_abs_qty = trade_list.total_abs_qty()
    if current_abs_qty ==0:
        return original_qty
    if max_abs_qty==0:
        return [0]*len(original_qty)
    max_abs_qty = float(max_abs_qty)
    ratio = max_abs_qty / current_abs_qty
    if ratio>=1.0:
        return original_qty

    new_qty = [abs(int(np.floor(ratio * qty))) for qty in trade_list.qty]
    new_qty_adjusted = reduce_trade_size_proportionally_to_abs_limit_per_leg(original_qty, new_qty)

    return new_qty_adjusted


def reduce_trade_size_proportionally_to_abs_limit_per_leg(trade_list_qty: list, abs_list: list) -> list:
    """

    :param trade_list_qty:
    :param abs_list:
    :return: list


    """
    # for each item in _trade and abs_list, return the signed minimum of the zip
    # eg if self._trade = [2,-2] and abs_list = [1,1], return [2,-2]

    assert all([x>=0 for x in abs_list])
    assert len(trade_list_qty) == len(abs_list)

    abs_trade_list = [abs(x) for x in trade_list_qty]
    smallest_abs_leg = min(abs_trade_list)
    if smallest_abs_leg == 0:
        # can't do this
        return [0 for x in trade_list_qty]

    abs_size_ratio_list = [
        min([x, y]) / float(x) for x, y in zip(abs_trade_list, abs_list)
    ]
    min_abs_size_ratio = min(abs_size_ratio_list)
    new_smallest_leg = np.floor(smallest_abs_leg * min_abs_size_ratio)
    ratio_applied = new_smallest_leg / smallest_abs_leg
    trade_list_with_ratio_as_float = [x * ratio_applied for x in trade_list_qty]
    trade_list_with_ratio_as_int = [int(x)
                                    for x in trade_list_with_ratio_as_float]
    diff = [
        abs(x - y)
        for x, y in zip(trade_list_with_ratio_as_float, trade_list_with_ratio_as_int)
    ]
    largediff = any([x > 0.0001 for x in diff])
    if largediff:
        trade_list_with_ratio_as_int = [0] * len(trade_list_qty)

    return trade_list_with_ratio_as_int


def reduce_trade_size_proportionally_so_smallest_leg_is_max_size(trade_list_qty: list, max_size: int):
    """
    Cut the trade down proportionally so the smallest leg is min_size

    :param max_size:
    :return: tradeQuantity


    """

    if max_size==0:
        return [0]*len(trade_list_qty)

    assert max_size > 0

    abs_trade_list = [abs(x) for x in trade_list_qty]
    smallest_abs_leg = min(abs_trade_list)

    if smallest_abs_leg==0:
        return trade_list_qty

    new_smallest_leg = max_size
    ratio_applied = new_smallest_leg / smallest_abs_leg
    if ratio_applied>=1.0:
        return trade_list_qty

    trade_list_with_ratio_as_float = [x * ratio_applied for x in trade_list_qty]
    trade_list_with_ratio_as_int = [int(x)
                                    for x in trade_list_with_ratio_as_float]
    diff = [
        abs(x - y)
        for x, y in zip(trade_list_with_ratio_as_float, trade_list_with_ratio_as_int)
    ]
    largediff = any([x > 0.0001 for x in diff])
    if largediff:
        return trade_list_qty

    return trade_list_with_ratio_as_int

