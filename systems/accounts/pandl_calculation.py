
import pandas as pd
import numpy as np

from syscore.objects import arg_not_supplied
from syscore.dateutils import ROOT_BDAYS_INYEAR, from_config_frequency_pandas_resample
from syscore.dateutils import Frequency, DAILY_PRICE_FREQ
from syscore.pdutils import spread_out_annualised_return_over_periods
from sysexecution.fills import listOfFills ## FEELS LIKE IT SHOULD BE MOVED
from sysquant.estimators.vol import robust_daily_vol_given_price


class pandlCalculation(object):
    def __init__(self,
                 price: pd.Series,
                 positions: pd.Series = arg_not_supplied,

                 fx: pd.Series = arg_not_supplied,
                 capital: pd.Series = arg_not_supplied,
                 value_per_point: float = 1.0,

                delayfill = False
                 ):

        self._price = price
        self._positions = positions
        self._fx = fx
        self._capital = capital
        self._value_per_point = value_per_point

        self._delayfill = delayfill


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

    def capital_as_pd_series_for_frequency(self,
                                           frequency: Frequency=DAILY_PRICE_FREQ) -> pd.Series:

        capital = self.capital
        resample_freq = from_config_frequency_pandas_resample(frequency)
        capital_at_frequency = capital.resample(resample_freq).ffill()

        return capital_at_frequency

    def as_pd_series_for_frequency(self,
                                   frequency: Frequency=DAILY_PRICE_FREQ,
                                   **kwargs) -> pd.Series:

        as_pd_series = self.as_pd_series(**kwargs)

        cum_returns = as_pd_series.cumsum()
        resample_freq = from_config_frequency_pandas_resample(frequency)
        cum_returns_at_frequency = cum_returns.resample(resample_freq, method="last")

        returns_at_frequency = cum_returns_at_frequency.diff()

        return returns_at_frequency


    def as_pd_series(self, percent = False):
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

        return  pandl_in_ccy

    def _pandl_in_instrument_ccy_given_points_pandl(self, pandl_in_points: pd.Series) -> pd.Series:
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
        positions = self._positions
        if self.delayfill:
            return positions.shift(1)
        else:
            return positions

    @property
    def delayfill(self) -> bool:
        return self._delayfill

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
                                  list_of_fills: listOfFills) -> pd.Series:
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


def unique_trades_df(trade_df: pd.DataFrame) -> pd.DataFrame:
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



curve_types = ['gross', 'net', 'costs']
GROSS_CURVE = 'gross'
NET_CURVE = 'net'
COSTS_CURVE = 'costs'

class pandlCalculationWithGenericCosts(pandlCalculation):

    def as_pd_series(self, percent = False, curve_type=NET_CURVE):
        if curve_type==NET_CURVE:
            if percent:
                return  self.net_percentage_pandl()
            else:
                return self.net_pandl_in_base_currency()

        elif curve_type==GROSS_CURVE:
            if percent:
                return self.percentage_pandl()
            else:
                return self.pandl_in_base_currency()
        elif curve_type==COSTS_CURVE:
            if percent:
                return self.costs_percentage_pandl()
            else:
                return self.costs_pandl_in_base_currency()

        else:
            raise Exception("Curve type %s not recognised! Must be one of %s" % (curve_type, curve_types))

    def net_percentage_pandl(self) -> pd.Series:
        gross = self.percentage_pandl()
        costs = self.costs_percentage_pandl()
        net = _add_gross_and_costs(gross, costs)

        return net

    def net_pandl_in_base_currency(self) -> pd.Series:
        gross = self.pandl_in_base_currency()
        costs = self.costs_pandl_in_base_currency()
        net = _add_gross_and_costs(gross, costs)

        return net

    def net_pandl_in_instrument_currency(self) -> pd.Series:
        gross = self.pandl_in_instrument_currency()
        costs = self.costs_pandl_in_instrument_currency()
        net = _add_gross_and_costs(gross, costs)

        return net

    def net_pandl_in_points(self) -> pd.Series:
        gross = self.pandl_in_points()
        costs = self.costs_pandl_in_points()
        net = _add_gross_and_costs(gross, costs)

        return net



    def costs_percentage_pandl(self) -> pd.Series:
        costs_in_base = self.costs_pandl_in_base_currency()
        costs = self._percentage_pandl_given_pandl(costs_in_base)

        return costs

    def costs_pandl_in_base_currency(self) -> pd.Series:
        costs_in_instr_ccy = self.costs_pandl_in_instrument_currency()
        costs_in_base = self._base_pandl_given_currency_pandl(costs_in_instr_ccy)

        return costs_in_base

    def costs_pandl_in_instrument_currency(self) -> pd.Series:
        costs_in_points = self.costs_pandl_in_points()
        costs_in_instr_ccy = self._pandl_in_instrument_ccy_given_points_pandl(costs_in_points)

        return costs_in_instr_ccy

    def costs_pandl_in_points(self) -> pd.Series:
        raise NotImplementedError

def _add_gross_and_costs(gross: pd.Series,
                        costs: pd.Series):
    costs_aligned = costs.reindex(gross.index, method="sum")

    net = gross + costs_aligned

    return net

## perhaps we should move the pandl for a forecast stuff inside here new class

class pandlCalculationWithSRCosts(pandlCalculationWithGenericCosts):
    def __init__(self, *args,
                 SR_cost: float,
                 daily_price_volatility: pd.Series = arg_not_supplied,
                 **kwargs):
        ## Is SR_cost a negative number?
        super().__init__(*args, **kwargs)
        self._SR_cost = SR_cost
        self._daily_price_volatility = daily_price_volatility

    def costs_pandl_in_points(self) -> pd.Series:
        SR_cost_as_annualised_figure = self.SR_cost_as_annualised_figure_points()

        position = self.positions

        SR_cost_per_period = calculate_SR_cost_per_period_of_position_data(position,
                                                                           SR_cost_as_annualised_figure)

        return SR_cost_per_period

    def SR_cost_as_annualised_figure_points(self) -> pd.Series:
        SR_cost_with_minus_sign = -self.SR_cost
        annualised_price_vol_points = self.annualised_price_volatility_points()

        return SR_cost_with_minus_sign * annualised_price_vol_points

    def annualised_price_volatility_points(self) -> pd.Series:
        return self.daily_price_volatility_points * ROOT_BDAYS_INYEAR

    @property
    def daily_price_volatility_points(self) -> pd.Series:
        daily_price_volatility = self._daily_price_volatility
        if daily_price_volatility is arg_not_supplied:
            daily_price_volatility = robust_daily_vol_given_price(self.price)

        return daily_price_volatility

    @property
    def SR_cost(self) -> float:
        return self._SR_cost

def calculate_SR_cost_per_period_of_position_data(position: pd.Series,
                                                  SR_cost_as_annualised_figure: pd.Series) -> pd.Series:
    # only want nans at the start
    position_ffill = position.ffill()

    ## We don't want to lose calculation because of warmup
    SR_cost_aligned_positions = SR_cost_as_annualised_figure.reindex(position_ffill.index, method="ffill")
    SR_cost_aligned_positions_backfilled = SR_cost_aligned_positions.bfill()

    # Don't include costs until we start trading
    SR_cost_aligned_positions_when_position_held = SR_cost_aligned_positions_backfilled[~position_ffill.isna()]

    # These will be annualised figure, make it a small loss every day
    SR_cost_per_period = spread_out_annualised_return_over_periods(SR_cost_aligned_positions_when_position_held)

    return SR_cost_per_period

