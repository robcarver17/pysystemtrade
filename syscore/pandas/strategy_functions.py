from copy import copy
from typing import Union, List

import numpy as np
import pandas as pd

from syscore.dateutils import BUSINESS_DAYS_IN_YEAR, SECONDS_IN_YEAR
from syscore.pandas.pdutils import uniquets


def turnover(
    x: pd.Series, y: Union[pd.Series, float, int], smooth_y_days: int = 250
) -> float:
    """
    Gives the turnover of x, once normalised for y

    Returned in annualised terms

    """

    daily_x = x.resample("1B").last()
    if isinstance(y, float) or isinstance(y, int):
        daily_y = pd.Series(np.full(daily_x.shape[0], float(y)), daily_x.index)
    else:
        daily_y = y.reindex(daily_x.index, method="ffill")
        ## need to apply a drag to this or will give zero turnover for constant risk
        daily_y = daily_y.ewm(smooth_y_days, min_periods=2).mean()

    x_normalised_for_y = daily_x / daily_y.ffill()

    avg_daily = float(x_normalised_for_y.diff().abs().mean())

    return avg_daily * BUSINESS_DAYS_IN_YEAR


def weights_sum_to_one(weights: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure that weights for ecah row sum up to one, except where all weights are zero

    Preserves nans

    >>> import datetime
    >>> df = pd.DataFrame(dict(a=[np.nan, np.nan, 0, 5,0, 2, 2], b=[0, np.nan, 0, np.nan,3,  3, 1]), index=pd.date_range(datetime.datetime(2000,1,1),periods=7))
    >>> weights_sum_to_one(df)
                       a         b
    2000-01-01       NaN  0.000000
    2000-01-02       NaN       NaN
    2000-01-03  0.000000  0.000000
    2000-01-04  1.000000       NaN
    2000-01-05  0.000000  1.000000
    2000-01-06  0.400000  0.600000
    2000-01-07  0.666667  0.333333

    """
    sum_weights = weights.sum(axis=1)
    zero_rows = sum_weights == 0.0
    sum_weights[zero_rows] = 0.0001  ## avoid Inf
    weight_multiplier = 1.0 / sum_weights
    weight_multiplier_array = np.array([weight_multiplier] * len(weights.columns))
    weight_values = weights.values

    normalised_weights_np = weight_multiplier_array.transpose() * weight_values
    normalised_weights = pd.DataFrame(
        normalised_weights_np, columns=weights.columns, index=weights.index
    )

    return normalised_weights


def drawdown(x: Union[pd.DataFrame, pd.Series]) -> Union[pd.DataFrame, pd.Series]:
    """
    Returns a ts of drawdowns for a time series x

    >>> import datetime
    >>> df = pd.DataFrame(dict(a=[1, 2, 3, 2,1 , 4, 5], b=[2, 2, 1, 2,4 , 6, 5]), index=pd.date_range(datetime.datetime(2000,1,1),periods=7))
    >>> drawdown(df)
                  a    b
    2000-01-01  0.0  0.0
    2000-01-02  0.0  0.0
    2000-01-03  0.0 -1.0
    2000-01-04 -1.0  0.0
    2000-01-05 -2.0  0.0
    2000-01-06  0.0  0.0
    2000-01-07  0.0 -1.0
    >>> s = pd.Series([1, 2, 3, 2,1 , 4, 5], index=pd.date_range(datetime.datetime(2000,1,1),periods=7))
    >>> drawdown(s)
    2000-01-01    0.0
    2000-01-02    0.0
    2000-01-03    0.0
    2000-01-04   -1.0
    2000-01-05   -2.0
    2000-01-06    0.0
    2000-01-07    0.0
    Freq: D, dtype: float64
    """
    maxx = x.expanding(min_periods=1).max()
    return x - maxx


def apply_abs_min(x: pd.Series, min_value: float = 0.1) -> pd.Series:
    """
    >>> import datetime
    >>> from syscore.pandas.pdutils import create_arbitrary_pdseries
    >>> s1=create_arbitrary_pdseries([1,2,3,-1,-2,-3], date_start = datetime.datetime(2000,1,1))
    >>> apply_abs_min(s1, 2)
    2000-01-03    2
    2000-01-04    2
    2000-01-05    3
    2000-01-06   -2
    2000-01-07   -2
    2000-01-10   -3
    Freq: B, dtype: int64
    """

    ## Could also use clip but no quicker and this is more intuitive
    x[(x < min_value) & (x > 0)] = min_value
    x[(x > -min_value) & (x < 0)] = -min_value

    return x


def replace_all_zeros_with_nan(pd_series: pd.Series) -> pd.Series:
    """
    >>> import datetime
    >>> d = datetime.datetime
    >>> date_index1 = [d(2000,1,1,23),d(2000,1,2,23),d(2000,1,3,23)]
    >>> s1 = pd.Series([0,5,6], index=date_index1)
    >>> replace_all_zeros_with_nan(s1)
    2000-01-01 23:00:00    NaN
    2000-01-02 23:00:00    5.0
    2000-01-03 23:00:00    6.0
    dtype: float64
    """
    copy_pd_series = copy(pd_series)
    copy_pd_series[copy_pd_series == 0.0] = np.nan

    if all(copy_pd_series.isna()):
        copy_pd_series[:] = np.nan

    return copy_pd_series


def spread_out_annualised_return_over_periods(data_as_annual: pd.Series) -> pd.Series:
    """
    >>> import datetime
    >>> d = datetime.datetime
    >>> date_index1 = [d(2000,1,1,23),d(2000,1,2,23),d(2000,1,3,23)]
    >>> s1 = pd.Series([0.365,0.730,0.365], index=date_index1)
    >>> spread_out_annualised_return_over_periods(s1)
    2000-01-01 23:00:00         NaN
    2000-01-02 23:00:00    0.001999
    2000-01-03 23:00:00    0.000999
    dtype: float64
    """
    period_intervals_in_seconds = (
        data_as_annual.index.to_series().diff().dt.total_seconds()
    )
    period_intervals_in_year_fractions = period_intervals_in_seconds / SECONDS_IN_YEAR
    data_per_period = data_as_annual * period_intervals_in_year_fractions

    return data_per_period


def calculate_cost_deflator(price: pd.Series) -> pd.Series:
    daily_returns = price_to_daily_returns(price)
    ## crude but doesn't matter
    vol_price = daily_returns.rolling(180, min_periods=3).std().ffill()
    final_vol = vol_price[-1]

    cost_scalar = vol_price / final_vol

    return cost_scalar


def price_to_daily_returns(price: pd.Series) -> pd.Series:
    daily_price = price.resample("1B").ffill()
    daily_returns = daily_price.ffill().diff()

    return daily_returns


def quantile_of_points_in_data_series(data_series: pd.Series) -> pd.Series:
    ## With thanks to https://github.com/PurpleHazeIan for this implementation
    numpy_series = np.array(data_series)
    results = []

    for irow in range(len(data_series)):
        current_value = numpy_series[irow]
        count_less_than = (numpy_series < current_value)[:irow].sum()
        results.append(count_less_than / (irow + 1))

    results_series = pd.Series(results, index=data_series.index)
    return results_series


def years_in_data(data: pd.Series) -> List[int]:
    """
    >>> import datetime
    >>> d = datetime.datetime
    >>> date_index1 = [d(2000,1,1),d(2002,1,2),d(2003,1,5)]
    >>> s1 = pd.Series([1,2,3], index=date_index1)
    >>> years_in_data(s1)
    [2000, 2002, 2003]
    """

    all_years = [x.year for x in data.index]
    unique_years = list(set(all_years))
    unique_years.sort()

    return unique_years


def fix_weights_vs_position_or_forecast(
    weights: pd.DataFrame, position_or_forecast: pd.DataFrame
) -> pd.DataFrame:
    """
    Take a matrix of weights and positions/forecasts (pdm) and align the weights to the forecasts/positions

    This deals with the problem of different rules and/or instruments having different history

    """

    # forward fill forecasts/positions
    pdm_ffill = position_or_forecast.ffill()

    ## Set leading all nan to zero so weights not set to zero
    p_or_f_notnan = ~pdm_ffill.isna()
    pdm_ffill[p_or_f_notnan.sum(axis=1) == 0] = 0

    # resample weights
    adj_weights = uniquets(weights)
    adj_weights = adj_weights.reindex(pdm_ffill.index, method="ffill")

    # ensure columns are aligned
    adj_weights = adj_weights[position_or_forecast.columns]

    # remove weights if nan forecast or position
    adj_weights[np.isnan(pdm_ffill)] = 0.0

    return adj_weights
