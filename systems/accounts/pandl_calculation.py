
"""
base currency p&l
local currency p&l
point p&l

from sysexecution.fills import listOfFills

position series

price series


What are the


"""


import pandas as pd
import numpy as np

from syscore.objects import arg_not_supplied
from sysexecution.fills import listOfFills ## FEELS LIKE IT SHOULD BE MOVED


class pandlCalculation(object):
    def __init__(self,
                 price: pd.Series,
                 positions: pd.Series = arg_not_supplied,

                 fx: pd.Series = arg_not_supplied,
                 capital: pd.Series = arg_not_supplied,
                 value_per_point: float = 1.0,

                 ):

        self._price = price
        self._positions = positions
        self._fx = fx
        self._capital = capital
        self._value_per_point = value_per_point


    @classmethod
    def using_positions_and_prices_merged_from_fills(pandlCalculation, price: pd.Series,
                                             positions: pd.Series,
                                             fills: listOfFills,
                                             **kwargs):

        merged_prices = merge_fill_prices_with_prices(price,
                                                      fills)

        return pandlCalculation(price = merged_prices,
                                positions=positions,
                                **kwargs)

    def percentage_pandl(self) -> pd.Series:
        capital = self.capital
        pandl_in_base = self.pandl_in_base_currency()
        capital_aligned = capital.reindex(pandl_in_base.index, method="ffill")

        return pandl_in_base / capital_aligned

    def pandl_in_base_currency(self) -> pd.Series:
        fx = self.fx
        pandl_in_ccy = self.pandl_in_instrument_currency()
        fx_aligned = fx.reindex(pandl_in_ccy.index, method="ffill")

        return pandl_in_ccy * fx_aligned

    def pandl_in_instrument_currency(self) -> pd.Series:
        pandl_in_points = self.pandl_in_points()
        point_size = self.value_per_point

        return pandl_in_points * point_size

    def pandl_in_points(self) -> pd.Series:
        positions = self.positions
        price_returns = self.price_returns
        pos_series = positions.groupby(positions.index).last()
        pos_series = pos_series.reindex(price_returns.index, method="ffill")

        returns = pos_series.shift(1) * price_returns

        returns[returns.isna()] = 0.0

        return returns

    @property
    def price_returns(self) -> pd.Series:
        prices = self.price
        price_returns = prices.ffill().diff()

        return price_returns

    @property
    def price(self) -> pd.Series:
        return self._price

    @property
    def positions(self) -> pd.Series:
        return self._positions

    @property
    def value_per_point(self) -> float:
        return self._value_per_point

    @property
    def fx(self) -> pd.Series:
        fx = self._fx
        if fx is arg_not_supplied:
            price_index = self.price.index
            fx = pd.Series([1.0] * len(price_index), price_index)

        return fx

    @property
    def capital(self) -> pd.Series:
        capital = self._capital
        if capital is arg_not_supplied:
            capital = 1.0

        if type(capital) is float or type(capital) is int:
            price_index = self.price.index
            capital = pd.Series([capital] * len(price_index), price_index)

        return capital



def merge_fill_prices_with_prices(prices: pd.Series,
                                  list_of_fills: listOfFills):

    list_of_trades_as_pd_df = list_of_fills.as_pd_df()
    unique_trades_as_pd_df = unique_trades_df(list_of_trades_as_pd_df)

    prices_to_use = pd.concat(
        [prices, unique_trades_as_pd_df.price], axis=1, join="outer")

    # Where no fill price available, use price
    prices_to_use = prices_to_use.fillna(axis=1, method="ffill")

    prices_to_use = prices_to_use.price

    prices_to_use = prices_to_use.replace([np.inf, -np.inf], np.nan)
    prices_to_use = prices_to_use.dropna()

    return prices_to_use

def unique_trades_df(trade_df: pd.DataFrame):
    cash_flow = trade_df.qty * trade_df.price
    trade_df["cash_flow"] = cash_flow
    new_df = trade_df.groupby(trade_df.index).sum()
    # qty and cash_flow will be correct, price won't be
    new_price = new_df.cash_flow / new_df.qty
    new_df["price"] = new_price
    new_df = new_df.drop("cash_flow", axis=1)

    return new_df


"""
Can have other class methods in future that allow you to just pass fills, trades, or something else


    @classmethod
    def using_fills(pandlCalculation, price: pd.Series,
                                             fills: listOfFills,
                                             **kwargs):
        
        positions = from_fills_to_positions(fills)

        merged_prices = merge_fill_prices_with_prices(price,
                                                      fills)

        return pandlCalculation(price=price,
                                positions=positions,
                                **kwargs)

    @classmethod
    def using_trades_inferring_fill_prices(pandlCalculation, price: pd.Series,
                                             trades: pd.Series,
                                             **kwargs):

        fills = from_trades_to_fills(trades, price)
        positions = from_fills_to_positions(fills)

        merged_prices = merge_fill_prices_with_prices(price,
                                                      fills)

        return pandlCalculation(price = price,
                                positions=positions,
                                **kwargs)


"""