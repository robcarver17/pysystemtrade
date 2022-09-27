import pandas as pd
import numpy as np

from syscore.objects import arg_not_supplied
from syscore.dateutils import from_config_frequency_pandas_resample
from syscore.dateutils import Frequency, DAILY_PRICE_FREQ


class pandlCalculation(object):
    def __init__(
        self,
        price: pd.Series,
        positions: pd.Series = arg_not_supplied,
        fx: pd.Series = arg_not_supplied,
        capital: pd.Series = arg_not_supplied,
        value_per_point: float = 1.0,
        roundpositions=False,
        delayfill=False,
    ):

        self._price = price
        self._positions = positions
        self._fx = fx
        self._capital = capital
        self._value_per_point = value_per_point

        self._delayfill = delayfill
        self._roundpositions = roundpositions

    def weight(self, weight: pd.Series):

        weighted_capital = apply_weighting(weight, self.capital)
        weighted_positions = apply_weighting(weight, self.positions)

        return pandlCalculation(
            self.price,
            positions=weighted_positions,
            fx=self.fx,
            capital=weighted_capital,
            value_per_point=self.value_per_point,
            roundpositions=self.roundpositions,
            delayfill=self.delayfill,
        )

    def capital_as_pd_series_for_frequency(
        self, frequency: Frequency = DAILY_PRICE_FREQ
    ) -> pd.Series:

        capital = self.capital
        resample_freq = from_config_frequency_pandas_resample(frequency)
        capital_at_frequency = capital.resample(resample_freq).ffill()

        return capital_at_frequency

    def as_pd_series_for_frequency(
        self, frequency: Frequency = DAILY_PRICE_FREQ, **kwargs
    ) -> pd.Series:

        as_pd_series = self.as_pd_series(**kwargs)

        resample_freq = from_config_frequency_pandas_resample(frequency)
        pd_series_at_frequency = as_pd_series.resample(resample_freq).sum()

        return pd_series_at_frequency

    def as_pd_series(self, percent=False):
        if percent:
            return self.percentage_pandl()
        else:
            return self.pandl_in_base_currency()

    def percentage_pandl(self) -> pd.Series:
        pandl_in_base = self.pandl_in_base_currency()

        pandl = self._percentage_pandl_given_pandl(pandl_in_base)

        return pandl

    def _percentage_pandl_given_pandl(self, pandl_in_base: pd.Series):
        capital = self.capital
        capital_aligned = capital.reindex(pandl_in_base.index, method="ffill")

        return 100.0 * pandl_in_base / capital_aligned

    def pandl_in_base_currency(self) -> pd.Series:
        pandl_in_ccy = self.pandl_in_instrument_currency()
        pandl_in_base = self._base_pandl_given_currency_pandl(pandl_in_ccy)

        return pandl_in_base

    def _base_pandl_given_currency_pandl(self, pandl_in_ccy) -> pd.Series:
        fx = self.fx
        fx_aligned = fx.reindex(pandl_in_ccy.index, method="ffill")

        return pandl_in_ccy * fx_aligned

    def pandl_in_instrument_currency(self) -> pd.Series:
        pandl_in_points = self.pandl_in_points()
        pandl_in_ccy = self._pandl_in_instrument_ccy_given_points_pandl(pandl_in_points)

        return pandl_in_ccy

    def _pandl_in_instrument_ccy_given_points_pandl(
        self, pandl_in_points: pd.Series
    ) -> pd.Series:
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
    def length_in_months(self) -> int:
        positions_monthly = self.positions.resample("1M").last()
        positions_ffill = positions_monthly.ffill()
        positions_no_nans = positions_ffill.dropna()

        return len(positions_no_nans.index)

    @property
    def positions(self) -> pd.Series:
        positions = self._get_passed_positions()
        if positions is arg_not_supplied:
            return arg_not_supplied

        positions_to_use = self._process_positions(positions)

        return positions_to_use

    def _process_positions(self, positions: pd.Series) -> pd.Series:
        if self.delayfill:
            positions_to_use = positions.shift(1)
        else:
            positions_to_use = positions

        if self.roundpositions:
            positions_to_use = positions_to_use.round()

        return positions_to_use

    def _get_passed_positions(self) -> pd.Series:
        positions = self._positions

        return positions

    @property
    def delayfill(self) -> bool:
        return self._delayfill

    @property
    def roundpositions(self) -> bool:
        return self._roundpositions

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
            align_index = self._index_to_align_capital_to
            capital = pd.Series([capital] * len(align_index), align_index)

        return capital

    @property
    def _index_to_align_capital_to(self):
        return self.price.index


def apply_weighting(weight: pd.Series, thing_to_weight: pd.Series) -> pd.Series:
    aligned_weight = weight.reindex(thing_to_weight.index).ffill()
    weighted_thing = thing_to_weight * aligned_weight

    return weighted_thing
