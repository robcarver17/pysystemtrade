import numpy as np

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
        prices_for_item = [element[idx] for element in self]
        prices_for_item = [
            price for price in prices_for_item if not np.isnan(price)]
        return float(np.mean(prices_for_item))