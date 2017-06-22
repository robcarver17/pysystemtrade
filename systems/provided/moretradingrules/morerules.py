import pandas as pd
import numpy as np
from systems.defaults import system_defaults
from copy import copy


def breakout(price, lookback, smooth=None):
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
        lookback,
        min_periods=int(min(len(price), np.ceil(lookback / 2.0)))).max()
    roll_min = price.rolling(
        lookback,
        min_periods=int(min(len(price), np.ceil(lookback / 2.0)))).min()

    roll_mean = (roll_max + roll_min) / 2.0

    # gives a nice natural scaling
    output = 40.0 * ((price - roll_mean) / (roll_max - roll_min))
    smoothed_output = output.ewm(
        span=smooth, min_periods=np.ceil(smooth / 2.0)).mean()

    return smoothed_output


def short_bias(price):
    """

    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.DataFrame

    :returns: pd.Series -- unscaled, uncapped forecast

    """

    avg_abs_forecast = system_defaults['average_absolute_forecast']

    forecast = -1.0 * avg_abs_forecast

    forecast_ts = copy(price)
    forecast_ts[:] = forecast

    return forecast_ts

def relative_carry(smoothed_carry_this_instrument, median_carry_for_asset_class):
    """
    Relative carry rule
    Suggested inputs: rawdata.smoothed_carry, rawdata.median_carry_for_asset_class

    :param smoothed_carry_this_instrument: pd.Series
    :param median_carry_for_asset_class: pd.Series aligned to smoothed_carry_this_instrument
    :return: forecast pd.Series
    """

    # should already be aligned
    relative_carry_forecast = smoothed_carry_this_instrument - median_carry_for_asset_class

    return relative_carry_forecast


def cross_sectional_mean_reversion(normalised_price_this_instrument, normalised_price_for_asset_class, horizon=250, ewma_span=None):
    """
    Cross sectional mean reversion within asset class

    :param normalised_price_this_instrument: pd.Series
    :param normalised_price_for_asset_class: pd.Series
    :return: pd.Series
    """

    if ewma_span is None:
        ewma_span = int(horizon / 4.0)

    ewma_span = max(ewma_span, 2)

    outperformance = normalised_price_this_instrument.ffill() - normalised_price_for_asset_class.ffill()
    relative_return = outperformance.diff()
    outperformance_over_horizon = pd.rolling_mean(relative_return, horizon)

    forecast = - pd.ewma(outperformance_over_horizon, span=ewma_span)

    return forecast

