import pandas as pd

from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.objects import arg_not_supplied
from syscore.pdutils import spread_out_annualised_return_over_periods
from sysquant.estimators.vol import robust_daily_vol_given_price
from systems.accounts.pandl_calculators.pandl_calculation import pandlCalculationWithGenericCosts


class pandlCalculationWithSRCosts(pandlCalculationWithGenericCosts):
    def __init__(self, *args,
                 SR_cost: float,
                 daily_returns_volatility: pd.Series = arg_not_supplied,
                 **kwargs):
        ## Is SR_cost a negative number?
        super().__init__(*args, **kwargs)
        self._SR_cost = SR_cost
        self._daily_returns_volatility = daily_returns_volatility

    def costs_pandl_in_points(self) -> pd.Series:
        SR_cost_as_annualised_figure = self.SR_cost_as_annualised_figure_points()

        position = self.positions
        price = self.price

        SR_cost_per_period = calculate_SR_cost_per_period_of_position_data_match_price_index(position,
                                                                                             price=price,
                                                                           SR_cost_as_annualised_figure=SR_cost_as_annualised_figure)



        return SR_cost_per_period

    def SR_cost_as_annualised_figure_points(self) -> pd.Series:
        SR_cost_with_minus_sign = -self.SR_cost
        annualised_price_vol_points = self.annualised_price_volatility_points()

        return SR_cost_with_minus_sign * annualised_price_vol_points

    def annualised_price_volatility_points(self) -> pd.Series:
        return self.daily_price_volatility_points * ROOT_BDAYS_INYEAR

    @property
    def daily_price_volatility_points(self) -> pd.Series:
        daily_price_volatility = self._daily_returns_volatility
        if daily_price_volatility is arg_not_supplied:
            daily_price_volatility = robust_daily_vol_given_price(self.price)

        return daily_price_volatility

    @property
    def SR_cost(self) -> float:
        return self._SR_cost


def calculate_SR_cost_per_period_of_position_data_match_price_index(position: pd.Series,
                                                  price: pd.Series,
                                                  SR_cost_as_annualised_figure: pd.Series) -> pd.Series:
    # only want nans at the start
    position_ffill = position.ffill()

    ## We don't want to lose calculation because of warmup
    SR_cost_aligned_positions = SR_cost_as_annualised_figure.reindex(position_ffill.index, method="ffill")
    SR_cost_aligned_positions_backfilled = SR_cost_aligned_positions.bfill()

    # Don't include costs until we start trading
    SR_cost_aligned_positions_when_position_held = SR_cost_aligned_positions_backfilled[~position_ffill.isna()]

    # Actually output in price space to match gross returns
    SR_cost_aligned_to_price = SR_cost_aligned_positions_when_position_held.reindex(price.index, method="ffill")

    # These will be annualised figure, make it a small loss every day
    SR_cost_per_period = spread_out_annualised_return_over_periods(SR_cost_aligned_to_price)

    return SR_cost_per_period