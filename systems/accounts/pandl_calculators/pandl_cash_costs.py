import datetime
import numpy as np
import pandas as pd

from syscore.pdutils import years_in_data, uniquets, calculate_cost_deflator
from syscore.dateutils import generate_equal_dates_within_year
from syscore.genutils import flatten_list

from systems.accounts.pandl_calculators.pandl_generic_costs import (
    pandlCalculationWithGenericCosts,
)
from systems.accounts.pandl_calculators.pandl_using_fills import (
    pandlCalculationWithFills,
)

from sysobjects.instruments import instrumentCosts
from sysobjects.fills import Fill


class pandlCalculationWithCashCostsAndFills(
    pandlCalculationWithGenericCosts, pandlCalculationWithFills
):
    def __init__(
        self,
        *args,
        raw_costs: instrumentCosts,
        rolls_per_year: int,
        vol_normalise_currency_costs: bool = True,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._raw_costs = raw_costs
        self._vol_normalise_currency_costs = vol_normalise_currency_costs
        self._rolls_per_year = rolls_per_year

    def costs_pandl_in_points(self) -> pd.Series:
        ## We work backwards since the cost calculator returns a currency cost
        costs_pandl_in_instrument_currency = self.costs_pandl_in_instrument_currency()
        block_price_multiplier = self.value_per_point
        costs_pandl_in_points = (
            costs_pandl_in_instrument_currency / block_price_multiplier
        )

        return costs_pandl_in_points

    def costs_pandl_in_instrument_currency(self) -> pd.Series:

        instrument_currency_costs_as_list = (
            self.costs_from_trading_in_instrument_currency_as_list()
        )
        date_index = self.date_index_for_all_fills()
        costs_as_pd_series = pd.Series(instrument_currency_costs_as_list, date_index)
        costs_as_pd_series = costs_as_pd_series.sort_index()
        costs_as_pd_series = uniquets(costs_as_pd_series)

        normalised_costs = self.normalise_costs_in_instrument_currency(
            costs_as_pd_series
        )

        return normalised_costs

    def costs_from_trading_in_instrument_currency_as_list(self) -> list:
        list_of_fills = self.list_of_all_fills()

        instrument_currency_costs = [
            -self.calculate_cost_instrument_currency_for_a_fill(fill)
            for fill in list_of_fills
        ]

        return instrument_currency_costs

    def date_index_for_all_fills(self) -> list:
        list_of_all_fills = self.list_of_all_fills()
        date_index = [fill.date for fill in list_of_all_fills]

        return date_index

    def list_of_all_fills(self) -> list:
        list_of_holding_fills = self.pseudo_fills_from_holding
        list_of_trading_fills = self.fills

        return list_of_trading_fills + list_of_holding_fills

    @property
    def pseudo_fills_from_holding(self) -> list:
        pseudo_fills = getattr(self, "_pseudo_fills", None)
        if pseudo_fills is None:
            self._pseudo_fills = pseudo_fills = self._calculate_pseudo_fills()

        return pseudo_fills

    def _calculate_pseudo_fills(self) -> list:
        list_of_years_in_data = years_in_data(self.positions)
        fills_by_year = [
            self._pseudo_fills_for_year(year) for year in list_of_years_in_data
        ]

        fills_as_single_list = flatten_list(fills_by_year)

        return fills_as_single_list

    def _pseudo_fills_for_year(self, year: int) -> list:
        rolls_per_year = self.rolls_per_year

        if rolls_per_year == 0:
            return []

        date_list = generate_equal_dates_within_year(year, rolls_per_year)
        average_holding_by_period = self._average_holdings_within_year(
            year, rolls_per_year
        )
        notional_price = 0  # doesn't actually affect costs
        last_date_with_positions = self.last_date_with_positions

        fills_this_year = [
            Fill(date=date, qty=qty, price=notional_price)
            for date, qty in zip(date_list, average_holding_by_period)
            if date<=last_date_with_positions
        ]

        return fills_this_year

    def _average_holdings_within_year(self, year: int, rolls_per_year: int) -> list:
        first_date = generate_equal_dates_within_year(year - 1, rolls_per_year)[-1]
        subsequent_dates = generate_equal_dates_within_year(year, rolls_per_year)
        all_dates = [first_date] + subsequent_dates

        list_of_average_holdings = []
        for date_index in range(len(subsequent_dates)):
            end_date = all_dates[date_index + 1]
            previous_date = all_dates[date_index]
            avg_holding = self._average_holding_for_period(previous_date, end_date)
            list_of_average_holdings.append(avg_holding)

        return list_of_average_holdings

    def _average_holding_for_period(
        self, previous_date: datetime.datetime, end_date: datetime.datetime
    ):
        positions = self.positions
        positions_in_period = positions[previous_date:end_date]
        avg_position = positions_in_period.abs().mean()
        if np.isnan(avg_position):
            return 0.0
        else:
            return avg_position

    @property
    def last_date_with_positions(self) -> datetime.datetime:
        return self.positions.index[-1]

    def normalise_costs_in_instrument_currency(self, costs_as_pd_series) -> pd.Series:

        dont_normalise_currency_costs = not self.vol_normalise_currency_costs
        if dont_normalise_currency_costs:
            return costs_as_pd_series

        cost_deflator = self.cost_deflator()
        reindexed_deflator = cost_deflator.reindex(costs_as_pd_series.index).ffill()

        normalised_costs = reindexed_deflator * costs_as_pd_series

        return normalised_costs

    def calculate_cost_instrument_currency_for_a_fill(self, fill: Fill) -> float:
        trade = fill.qty
        price = fill.price

        block_price_multiplier = self.value_per_point
        cost_for_trade = self.raw_costs.calculate_cost_instrument_currency(
            blocks_traded=trade,
            price=price,
            block_price_multiplier=block_price_multiplier,
        )

        return cost_for_trade

    def cost_deflator(self):
        cost_deflator = getattr(self, "_cost_deflator", None)
        if cost_deflator is None:
            self._cost_deflator = cost_deflator = self._calculate_cost_deflator()

        return cost_deflator

    def _calculate_cost_deflator(self) -> pd.Series:
        ## adjusts costs according to price vol
        price = self.price

        cost_scalar = calculate_cost_deflator(price)

        return cost_scalar

    @property
    def raw_costs(self) -> instrumentCosts:
        return self._raw_costs

    @property
    def vol_normalise_currency_costs(self) -> bool:
        return self._vol_normalise_currency_costs

    @property
    def rolls_per_year(self) -> int:
        return self._rolls_per_year
