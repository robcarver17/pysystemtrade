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


def longonly(price, shortonly):
    """
    Long or short only

    To work requires a second data item "data.shortonly" which returns a bool

    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.DataFrame

    :param shortonly: Go short, or long
    :type shortonly: bool


    :returns: pd.Series -- unscaled, uncapped forecast

    """

    assert shortonly is bool

    avg_abs_forecast = system_defaults['average_absolute_forecast']

    if shortonly:
        forecast = -1.0 * avg_abs_forecast
    else:
        forecast = avg_abs_forecast

    forecast_ts = copy(price)
    forecast_ts[:] = forecast

    return forecast_ts
