import pandas as pd
import numpy as np
from sysquant.estimators.vol import robust_daily_vol_given_price, robust_vol_calc


def ewmac(price, vol, Lfast, Lslow):
    """
    Calculate the ewmac trading fule forecast, given a price and EWMA speeds Lfast, Lslow and vol_lookback

    Assumes that 'price' and vol is daily data

    This version uses a precalculated price volatility, and does not do capping or scaling

    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.Series

    :param vol: The daily price unit volatility (NOT % vol)
    :type vol: pd.Series aligned to price

    :param Lfast: Lookback for fast in days
    :type Lfast: int

    :param Lslow: Lookback for slow in days
    :type Lslow: int

    :returns: pd.DataFrame -- unscaled, uncapped forecast


    >>> from systems.tests.testdata import get_test_object_futures
    >>> from systems.basesystem import System
    >>> (rawdata, data, config)=get_test_object_futures()
    >>> system=System( [rawdata], data, config)
    >>>
    >>> ewmac(rawdata.get_daily_prices("EDOLLAR"), rawdata.daily_returns_volatility("EDOLLAR"), 64, 256).tail(2)
    2015-12-10    5.327019
    2015-12-11    4.927339
    Freq: B, dtype: float64
    """
    # price: This is the stitched price series
    # We can't use the price of the contract we're trading, or the volatility will be jumpy
    # And we'll miss out on the rolldown. See
    # https://qoppac.blogspot.com/2015/05/systems-building-futures-rolling.html

    # We don't need to calculate the decay parameter, just use the span
    # directly

    fast_ewma = price.ewm(span=Lfast).mean()
    slow_ewma = price.ewm(span=Lslow).mean()
    raw_ewmac = fast_ewma - slow_ewma

    return raw_ewmac / vol.ffill()


def breakout(price, lookback=10, smooth=None):
    """
    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.DataFrame

    :param lookback: Lookback in days
    :type lookback: int

    :param lookback: Smooth to apply in days. Must be less than lookback! Defaults to smooth/4
    :type lookback: int

    :returns: pd.DataFrame -- unscaled, uncapped forecast

    With thanks to nemo4242 on elitetrader.com for vectorisation

    """
    if smooth is None:
        smooth = max(int(lookback / 4.0), 1)

    assert smooth < lookback

    roll_max = price.rolling(
        lookback, min_periods=int(min(len(price), np.ceil(lookback / 2.0)))
    ).max()
    roll_min = price.rolling(
        lookback, min_periods=int(min(len(price), np.ceil(lookback / 2.0)))
    ).min()

    roll_mean = (roll_max + roll_min) / 2.0

    # gives a nice natural scaling
    output = 40.0 * ((price - roll_mean) / (roll_max - roll_min))
    smoothed_output = output.ewm(span=smooth, min_periods=np.ceil(smooth / 2.0)).mean()

    return smoothed_output


def cross_sectional_mean_reversion(
    normalised_price_this_instrument,
    normalised_price_for_asset_class,
    horizon=250,
    ewma_span=None,
):
    """
    Cross sectional mean reversion within asset class

    :param normalised_price_this_instrument: pd.Series
    :param normalised_price_for_asset_class: pd.Series
    :return: pd.Series
    """

    if ewma_span is None:
        ewma_span = int(horizon / 4.0)

    ewma_span = max(ewma_span, 2)

    outperformance = (
        normalised_price_this_instrument.ffill()
        - normalised_price_for_asset_class.ffill()
    )
    relative_return = outperformance.diff()
    outperformance_over_horizon = relative_return.rolling(horizon).mean()

    forecast = -outperformance_over_horizon.ewm(span=ewma_span).mean()

    return forecast


def relative_momentum(
    normalised_price_this_instrument,
    normalised_price_for_asset_class,
    horizon=250,
    ewma_span=None,
):
    """
    Cross sectional mean reversion within asset class

    :param normalised_price_this_instrument: pd.Series
    :param normalised_price_for_asset_class: pd.Series
    :return: pd.Series
    """

    if ewma_span is None:
        ewma_span = int(horizon / 4.0)

    ewma_span = max(ewma_span, 2)

    outperformance = (
        normalised_price_this_instrument.ffill()
        - normalised_price_for_asset_class.ffill()
    )
    outperformance[outperformance == 0] = np.nan
    average_outperformance_over_horizon = (outperformance - outperformance.shift(horizon))/horizon

    forecast = average_outperformance_over_horizon.ewm(span=ewma_span).mean()

    return forecast


def carry(raw_carry, smooth_days=90):
    """
    Calculate carry forecast, given that there exists a raw_carry() in rawdata

    Assumes that everything is daily data

    :param raw_carry: The annualised sharpe ratio of rolldown
    :type raw_carry: pd.DataFrame (assumed Tx1)

    >>> from systems.tests.testdata import get_test_object_futures
    >>> from systems.basesystem import System
    >>> (rawdata, data, config)=get_test_object_futures()
    >>> system=System( [rawdata], data, config)
    >>>
    >>> carry2(rawdata.raw_carry("EDOLLAR")).tail(2)
    2015-12-10    0.411686
    2015-12-11    0.411686
    Freq: B, dtype: float64
    """

    smooth_carry = raw_carry.ewm(smooth_days).mean()

    return smooth_carry


def ewmac_calc_vol(price, Lfast, Lslow, vol_days=35):
    """
    Calculate the ewmac trading fule forecast, given a price and EWMA speeds Lfast, Lslow and vol_lookback

    Assumes that 'price' and vol is daily data

    This version recalculates the price volatility, and does not do capping or scaling

    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.Series

    :param Lfast: Lookback for fast in days
    :type Lfast: int

    :param Lslow: Lookback for slow in days
    :type Lslow: int

    :returns: pd.DataFrame -- unscaled, uncapped forecast


    >>> from systems.tests.testdata import get_test_object_futures
    >>> from systems.basesystem import System
    >>> (rawdata, data, config)=get_test_object_futures()
    >>> system=System( [rawdata], data, config)
    >>>
    >>> ewmac(rawdata.get_daily_prices("EDOLLAR"), rawdata.daily_returns_volatility("EDOLLAR"), 64, 256).tail(2)
    2015-12-10    5.327019
    2015-12-11    4.927339
    Freq: B, dtype: float64
    """
    # price: This is the stitched price series
    # We can't use the price of the contract we're trading, or the volatility will be jumpy
    # And we'll miss out on the rolldown. See
    # https://qoppac.blogspot.com/2015/05/systems-building-futures-rolling.html

    # We don't need to calculate the decay parameter, just use the span
    # directly

    fast_ewma = price.ewm(span=Lfast).mean()
    slow_ewma = price.ewm(span=Lslow).mean()
    raw_ewmac = fast_ewma - slow_ewma

    vol = robust_daily_vol_given_price(price, days=vol_days)

    return raw_ewmac / vol.ffill()


def relative_carry(smoothed_carry_this_instrument, median_carry_for_asset_class):
    """
    Relative carry rule
    Suggested inputs: rawdata.smoothed_carry, rawdata.median_carry_for_asset_class

    :param smoothed_carry_this_instrument: pd.Series
    :param median_carry_for_asset_class: pd.Series aligned to smoothed_carry_this_instrument
    :return: forecast pd.Series
    """

    # should already be aligned
    relative_carry_forecast = (
        smoothed_carry_this_instrument - median_carry_for_asset_class
    )

    return relative_carry_forecast


def factor_trading_rule(demean_factor_value, smooth=90):
    vol = robust_vol_calc(demean_factor_value)
    normalised_factor_value = demean_factor_value / vol
    smoothed_normalised_factor_value = normalised_factor_value.ewm(span=smooth).mean()

    return smoothed_normalised_factor_value


def conditioned_factor_trading_rule(
    demean_factor_value, condition_demean_factor_value, smooth=90
):
    vol = robust_vol_calc(demean_factor_value)
    normalised_factor_value = demean_factor_value / vol

    sign_condition = condition_demean_factor_value.apply(np.sign)
    sign_condition_resample = sign_condition.reindex(
        normalised_factor_value.index
    ).ffill()

    conditioned_factor = normalised_factor_value * sign_condition_resample
    smoothed_conditioned_factor = conditioned_factor.ewm(span=smooth).mean()

    return smoothed_conditioned_factor


def mr_wings(price, vol, Lfast=4):
    Lslow = Lfast * 4
    ewmac_signal = ewmac(price, vol, Lfast, Lslow)
    ewmac_std = ewmac_signal.rolling(5000, min_periods=3).std()
    ewmac_signal[ewmac_signal.abs() < ewmac_std * 3] = 0.0
    mr_signal = -ewmac_signal

    return mr_signal


def accel(price, vol, Lfast=4):
    Lslow = Lfast * 4
    ewmac_signal = ewmac(price, vol, Lfast, Lslow)

    accel = ewmac_signal - ewmac_signal.shift(Lfast)

    return accel
