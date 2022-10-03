import numpy as np
import datetime

import pandas as pd

from sysexecution.trade_qty import listOfTradeQuantity, tradeQuantity


class listOfFillDatetime(list):
    def final_fill_datetime(self):
        valid_dates = [dt for dt in self if dt is not None]

        return max(valid_dates)


class listOfOrders(list):
    def as_pd(self) -> pd.DataFrame:
        date_list = [order.fill_datetime for order in self]
        key_list = [order.key for order in self]
        trade_list = [order.trade for order in self]
        fill_list = [order.fill for order in self]
        id_list = [order.order_id for order in self]
        price_list = [order.filled_price for order in self]

        pd_df = pd.DataFrame(
            dict(
                fill_datetime=date_list,
                key=key_list,
                trade=trade_list,
                fill=fill_list,
                price=price_list,
            ),
            index=id_list,
        )

        return pd_df

    def as_pd_with_limits(self) -> pd.DataFrame:
        date_list = [order.fill_datetime for order in self]
        key_list = [order.key for order in self]
        trade_list = [order.trade for order in self]
        fill_list = [order.fill for order in self]
        id_list = [order.order_id for order in self]
        price_list = [order.filled_price for order in self]
        limit_list = [order.limit_price for order in self]

        pd_df = pd.DataFrame(
            dict(
                fill_datetime=date_list,
                key=key_list,
                trade=trade_list,
                fill=fill_list,
                price=price_list,
                limit = limit_list
            ),
            index=id_list,
        )

        return pd_df


    def list_of_filled_price(self) -> list:
        list_of_filled_price = [order.filled_price for order in self]

        return list_of_filled_price

    def average_fill_price(self) -> float:
        def _nan_for_none(x):
            if x is None:
                return np.nan
            else:
                return x

        list_of_filled_price = self.list_of_filled_price()
        list_of_filled_price = [_nan_for_none(x) for x in list_of_filled_price]
        average_fill_price = np.nanmean(list_of_filled_price)

        if np.isnan(average_fill_price):
            return None

        return average_fill_price

    def list_of_filled_datetime(self) -> listOfFillDatetime:
        list_of_filled_datetime = listOfFillDatetime(
            [order.fill_datetime for order in self]
        )

        return list_of_filled_datetime

    def final_fill_datetime(self) -> datetime.datetime:
        list_of_filled_datetime = self.list_of_filled_datetime()
        final_fill_datetime = list_of_filled_datetime.final_fill_datetime()

        return final_fill_datetime

    def list_of_filled_qty(self) -> listOfTradeQuantity:
        list_of_filled_qty = [order.fill for order in self]
        list_of_filled_qty = listOfTradeQuantity(list_of_filled_qty)

        return list_of_filled_qty

    def total_filled_qty(self) -> tradeQuantity:
        list_of_filled_qty = self.list_of_filled_qty()

        return list_of_filled_qty.total_filled_qty()

    def all_zero_fills(self) -> bool:
        list_of_filled_qty = self.list_of_filled_qty()
        zero_fills = [fill.equals_zero() for fill in list_of_filled_qty]

        return all(zero_fills)
