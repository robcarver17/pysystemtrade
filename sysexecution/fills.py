from collections import namedtuple

import pandas as pd

from syscore.genutils import list_of_ints_with_highest_common_factor_positive_first
from syscore.objects import missing_order
from sysexecution.orders.base_orders import Order
from sysexecution.orders.list_of_orders import listOfOrders

Fill = namedtuple("Fill", ["date", "qty", "price"])


class listOfFills(list):
    def __init__(self, list_of_fills):
        list_of_fills = [
            fill for fill in list_of_fills if fill is not missing_order]
        super().__init__(list_of_fills)

    @classmethod
    def from_list_of_orders(listOfFills, list_of_orders: listOfOrders):
        order_list_as_fills = [fill_from_order(order) for order in list_of_orders]
        list_of_fills = listOfFills(order_list_as_fills)

        return list_of_fills

    def _as_dict_of_lists(self) -> dict:
        qty_list = [fill.qty for fill in self]
        price_list = [fill.price for fill in self]
        date_list = [fill.date for fill in self]

        return dict(qty=qty_list, price=price_list, date=date_list)

    def as_pd_df(self) -> pd.DataFrame:
        self_as_dict = self._as_dict_of_lists()
        date_index = self_as_dict.pop("date")
        df = pd.DataFrame(self_as_dict, index=date_index)
        df = df.sort_index()

        return df


def fill_from_order(order: Order) -> Fill:
    try:
        assert len(order.trade)==1
    except:
        raise Exception("Can't get fills from multi-leg orders")

    if order.fill_equals_zero():
        return missing_order

    fill_price = order.filled_price
    fill_datetime = order.fill_datetime
    fill_qty = order.fill[0]

    if fill_price is None:
        return missing_order

    if fill_datetime is None:
        return missing_order

    return Fill(fill_datetime, fill_qty, fill_price)


def from_fill_list_to_fill_price(fill_list, filled_price_list) -> float:
    if type(filled_price_list) is float or type(filled_price_list) is int:
        return filled_price_list

    if filled_price_list is None:
        return None

    if len(filled_price_list)==1:
        return filled_price_list[0]

    if fill_list is None:
        return None

    assert len(filled_price_list)==len(fill_list)

    fill_list_as_common_factor = list_of_ints_with_highest_common_factor_positive_first(fill_list)
    fill_price = [x*y for x,y in zip(fill_list_as_common_factor, filled_price_list)]

    return sum(fill_price)