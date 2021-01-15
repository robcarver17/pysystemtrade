from collections import namedtuple

import numpy as np
import pandas as pd

from syscore.objects import missing_order
from sysexecution.orders.base_orders import Order
from sysexecution.orders.list_of_orders import listOfOrders

from sysexecution.trade_qty import tradeQuantity


class fillPrice(list):
    def __init__(self, fill_price):
        if fill_price is None:
            fill_price = []
        if isinstance(fill_price, fillPrice):
            fill_price = list(fill_price)
        elif (isinstance(fill_price, float)) or (isinstance(fill_price, int)):
            fill_price = [fill_price]

        super().__init__(fill_price)

    @classmethod
    def empty_size_trade_qty(fillPrice, trade_qty: tradeQuantity):
        fill_price = [np.nan] * len(trade_qty)
        return fillPrice(fill_price)

    def is_empty(self):
        if len(self)==0:
            return True
        return all([np.isnan(x) for x in self])

    def sort_with_idx(self, idx_list):
        unsorted = self
        price_sorted = [unsorted[idx] for idx in idx_list]
        self = fillPrice(price_sorted)


class listOfFillPrice(list):
    def average_fill_price(self) -> fillPrice:
        len_items = len(self[0])  # assumes all the same length
        averages = [self._average_price_for_items_with_idx(idx) for idx in range(len_items)]
        return fillPrice(averages)

    def _average_price_for_items_with_idx(self, idx) -> float:
        prices_for_item = [element.price[idx] for element in self]
        prices_for_item = [
            price for price in prices_for_item if not np.isnan(price)]
        return float(np.mean(prices_for_item))


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
    if order.fill_equals_zero():
        return missing_order

    fill_price = order.filled_price
    fill_datetime = order.fill_datetime
    fill_qty = order.fill

    if fill_price.is_empty():
        return missing_order

    if fill_datetime is None:
        return missing_order

    return Fill(fill_datetime, fill_qty, fill_price)