import pandas as pd

from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.constants import arg_not_supplied
from syscore.pandas.strategy_functions import spread_out_annualised_return_over_periods
from sysquant.estimators.vol import robust_daily_vol_given_price
from systems.accounts.pandl_calculators.pandl_generic_costs import (
    pandlCalculationWithGenericCosts,
)
from systems.accounts.pandl_calculators.pandl_calculation import apply_weighting


class pandlCalculationWithSRCosts(pandlCalculationWithGenericCosts):
    def __init__(
        self,
        *args,
        SR_cost: float,
        average_position: pd.Series,
        daily_returns_volatility: pd.Series = arg_not_supplied,
        **kwargs,
    ):
        ## Is SR_cost a negative number?
        super().__init__(*args, **kwargs)
        self._SR_cost = SR_cost
        self._daily_returns_volatility = daily_returns_volatility
        self._average_position = average_position

    def weight(self, weight: pd.Series):
        ## we don't weight fills, instead will be inferred from positions
        weighted_capital = apply_weighting(weight, self.capital)
        weighted_positions = apply_weighting(weight, self.positions)
        weighted_average_position = apply_weighting(weight, self.average_position)

        return pandlCalculationWithSRCosts(
            positions=weighted_positions,
            capital=weighted_capital,
            average_position=weighted_average_position,
            price=self.price,
            fx=self.fx,
            SR_cost=self._SR_cost,
            daily_returns_volatility=self.daily_returns_volatility,
            value_per_point=self.value_per_point,
            roundpositions=self.roundpositions,
            delayfill=self.delayfill,
        )

    def costs_pandl_in_points(self) -> pd.Series:
        SR_cost_as_annualised_figure = self.SR_cost_as_annualised_figure_points()

        position = self.positions
        price = self.price

        SR_cost_per_period = (
            calculate_SR_cost_per_period_of_position_data_match_price_index(
                position,
                price=price,
                SR_cost_as_annualised_figure=SR_cost_as_annualised_figure,
            )
        )

        return SR_cost_per_period

    def SR_cost_as_annualised_figure_points(self) -> pd.Series:
        SR_cost_with_minus_sign = -self.SR_cost
        annualised_price_vol_points_for_an_average_position = (
            self.points_vol_of_an_average_position()
        )

        return (
            SR_cost_with_minus_sign
            * annualised_price_vol_points_for_an_average_position
        )

    def points_vol_of_an_average_position(self) -> pd.Series:
        average_position = self.average_position
        annualised_price_vol_points = self.annualised_price_volatility_points()

        average_position_aligned_to_vol = average_position.reindex(
            annualised_price_vol_points.index, method="ffill"
        )

        return average_position_aligned_to_vol * annualised_price_vol_points

    def annualised_price_volatility_points(self) -> pd.Series:
        return self.daily_price_volatility_points * ROOT_BDAYS_INYEAR

    @property
    def daily_price_volatility_points(self) -> pd.Series:
        daily_price_volatility = self.daily_returns_volatility
        if daily_price_volatility is arg_not_supplied:
            daily_price_volatility = robust_daily_vol_given_price(self.price)

        return daily_price_volatility

    @property
    def daily_returns_volatility(self) -> pd.Series:
        return self._daily_returns_volatility

    @property
    def SR_cost(self) -> float:
        return self._SR_cost

    @property
    def average_position(self) -> pd.Series:
        return self._average_position


def calculate_SR_cost_per_period_of_position_data_match_price_index(
    position: pd.Series, price: pd.Series, SR_cost_as_annualised_figure: pd.Series
) -> pd.Series:
    # only want nans at the start
    position_ffill = position.ffill()

    ## We don't want to lose calculation because of warmup
    SR_cost_aligned_positions = SR_cost_as_annualised_figure.reindex(
        position_ffill.index, method="ffill"
    )
    SR_cost_aligned_positions_backfilled = SR_cost_aligned_positions.bfill()

    # Don't include costs until we start trading
    SR_cost_aligned_positions_when_position_held = SR_cost_aligned_positions_backfilled[
        ~position_ffill.isna()
    ]

    # Actually output in price space to match gross returns
    SR_cost_aligned_to_price = SR_cost_aligned_positions_when_position_held.reindex(
        price.index, method="ffill"
    )

    # These will be annualised figure, make it a small loss every day
    SR_cost_per_period = spread_out_annualised_return_over_periods(
        SR_cost_aligned_to_price
    )

    return SR_cost_per_period
