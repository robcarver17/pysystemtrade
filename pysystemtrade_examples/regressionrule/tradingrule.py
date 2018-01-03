import pandas as pd
import numpy as np
from syscore.dateutils import UNIXTIME_IN_YEAR


def my_regr(df, idx=None, timewindow=None, min_periods=10):
    """
    Runs a single regression at point idx, using window length window, returning gradient / beta

    :param df: stuff to regress over
    :type df: pd.Series with columns ['y','x']

    :param idx: where we are in time - uses all previous data
    :type idx: int or None (in which does entire data frame)

    :param timewindow: Rolling window to run regression over
    :type timewindow: int

    :param min_periods: minimum amount of data to use
    :type min_periods: int

    :returns: float

    """

    ## default to regressing from last point in data
    if idx is None:
        idx = len(df.index) - 1

    ## default to using entire data frame for regression
    if timewindow is None:
        timewindow = len(df.index)

    data_start = max(idx - timewindow + 1, 0)

    df_subset = df[data_start:idx]

    ## remove nans in both x andd y
    clean_x = [
        xvalue
        for (xvalue,
             yvalue) in zip(df_subset["x"].values, df_subset["y"].values)
        if not (np.isnan(xvalue) or np.isnan(yvalue))
    ]
    clean_y = [
        yvalue
        for (xvalue,
             yvalue) in zip(df_subset["x"].values, df_subset["y"].values)
        if not (np.isnan(xvalue) or np.isnan(yvalue))
    ]

    ## enforce minimum amount of data
    if len(clean_x) < min_periods:
        return np.nan

    ## do the regression
    gradient, intercept = np.polyfit(clean_x, clean_y, 1)

    return gradient


def regression_rule(price, volatility, timewindow=256, min_periods=10):
    """
    Runs the regression rule to detect trends

    :param price: price to check, assumed to be week day frequency
    :type price: pd.Series

    :param volatility: vol to standardise price change by
    :type volatility: pd.Series (same dimensions and index as price)

    :param timewindow: Rolling window to run regression over, week day frequency
    :type timewindow: int

    :returns: pd.Series (same dimensions and index as price)

    """

    assert type(timewindow) is int

    ## Create a time index where 1.0 is one year
    ## internal pandas implementation of date time is unix time

    rawx = list(price.index.astype(np.int64))
    x = [(xvalue - rawx[0]) / UNIXTIME_IN_YEAR for xvalue in rawx]
    x = pd.Series(x, price.index)

    ## For regression y=mx + b, where y is price, m is gradient or forecast value
    df = pd.concat([price, x], axis=1)
    df.columns = ["y", "x"]

    ## Rolling regression, returns gradient which is also forecast
    ols_ans = [
        my_regr(
            df, idx=idx_start, timewindow=timewindow, min_periods=min_periods)
        for idx_start in range(len(df.index))
    ]

    ols_ans = pd.Series(ols_ans, index=price.index)

    ols_ans = ols_ans / volatility

    return (ols_ans)
