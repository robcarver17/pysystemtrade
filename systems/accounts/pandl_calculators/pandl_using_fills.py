import numpy as np
import pandas as pd

from syscore.constants import missing_data, arg_not_supplied
from systems.accounts.pandl_calculators.pandl_calculation import (
    pandlCalculation,
    apply_weighting,
)

from sysobjects.fills import listOfFills, Fill


class pandlCalculationWithFills(pandlCalculation):
    def __init__(self, *args, fills: listOfFills = arg_not_supplied, **kwargs):
        # if fills aren't supplied, can be inferred from positions
        super().__init__(*args, **kwargs)
        self._fills = fills
        self._calculated_price = missing_data

    def weight(self, weight: pd.Series):
        ## we don't weight fills, instead will be inferred from positions
        weighted_capital = apply_weighting(weight, self.capital)
        weighted_positions = apply_weighting(weight, self.positions)

        return pandlCalculationWithFills(
            self.price,
            positions=weighted_positions,
            fx=self.fx,
            capital=weighted_capital,
            value_per_point=self.value_per_point,
            roundpositions=self.roundpositions,
            delayfill=self.delayfill,
        )

    @classmethod
    def using_positions_and_prices_merged_from_fills(
        pandlCalculation,
        price: pd.Series,
        positions: pd.Series,
        fills: listOfFills,
        **kwargs,
    ):

        merged_prices = merge_fill_prices_with_prices(price, fills)

        return pandlCalculation(price=merged_prices, positions=positions, **kwargs)

    @property
    def fills(self) -> listOfFills:
        fills = self._fills
        if fills is arg_not_supplied:
            # Infer from positions
            # positions will have delayfill and round applied to them already
            fills = self._infer_fills_from_position()
            self._fills = fills

        ## Fills passed in directly are expected to be precise, so we don't round or delay them

        return fills

    def _infer_fills_from_position(self) -> listOfFills:

        # positions will have delayfill and round applied to them already
        positions = self.positions
        if positions is arg_not_supplied:
            raise Exception("Need to pass fills or positions")

        fills = listOfFills.from_position_series_and_prices(
            positions=positions, price=self.price
        )
        return fills

    @property
    def positions(self) -> pd.Series:
        positions = self._get_passed_positions()
        if positions is arg_not_supplied:
            ## fills will already have delay and round positions applied
            positions = self._infer_position_from_fills()
            self._positions = positions
            return positions
        else:
            positions_to_use = self._process_positions(positions)
            return positions_to_use

    def _infer_position_from_fills(self) -> pd.Series:
        fills = self._fills
        if fills is arg_not_supplied:
            raise Exception("Need to pass fills or positions")

        positions = infer_positions_from_fills(fills)

        return positions

    def _calculate_and_set_prices_from_fills_and_input_prices(self) -> pd.Series:

        ## this will be set in the parent __init__
        passed_prices = self._price
        merged_price = merge_fill_prices_with_prices(passed_prices, self.fills)
        self._calculated_price = merged_price

        return merged_price


def merge_fill_prices_with_prices(
    prices: pd.Series, list_of_fills: listOfFills
) -> pd.Series:
    list_of_trades_as_pd_df = list_of_fills.as_pd_df()
    unique_trades_as_pd_df = unique_trades_df(list_of_trades_as_pd_df)

    prices_to_use = pd.concat(
        [prices, unique_trades_as_pd_df.price], axis=1, join="outer"
    )
    prices_to_use.columns = ["price", "fill_price"]

    # Where no fill price available, use price
    prices_to_use = prices_to_use.fillna(axis=1, method="ffill")

    prices_to_use = prices_to_use.fill_price

    prices_to_use = prices_to_use.replace([np.inf, -np.inf], np.nan)
    prices_to_use = prices_to_use.dropna()

    return prices_to_use


def unique_trades_df(trade_df: pd.DataFrame) -> pd.DataFrame:
    cash_flow = trade_df.qty * trade_df.price
    trade_df["cash_flow"] = cash_flow
    new_df = trade_df.groupby(trade_df.index).sum()
    # qty and cash_flow will be correct, price won't be
    new_price = new_df.cash_flow / new_df.qty
    new_df["price"] = new_price
    new_df = new_df.drop(labels="cash_flow", axis=1)

    return new_df


def infer_positions_from_fills(fills: listOfFills) -> pd.Series:
    date_index = [fill.date for fill in fills]
    qty_trade = [fill.qty for fill in fills]
    trade_series = pd.Series(qty_trade, index=date_index)
    trade_series = trade_series.sort_index()
    position_series = trade_series.cumsum()

    return position_series


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
