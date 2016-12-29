"""
Utilities to help with pandas
"""

import pandas as pd
import numpy as np
from syscore.fileutils import get_filename_for_package
from syscore.dateutils import BUSINESS_DAYS_IN_YEAR


def turnover(x, y):
    """
    Gives the turnover of x, once normalised for y

    Returned in annualised terms
    """

    if isinstance(y, float):
        y = pd.Series([y] * len(x.index), x.index)

    norm_x = x / y.ffill()

    avg_daily = float(norm_x.diff().abs().resample("1B", how="sum").mean())

    return avg_daily * BUSINESS_DAYS_IN_YEAR


def uniquets(x):
    """
    Makes x unique
    """
    x = x.groupby(level=0).last()
    return x


def df_from_list(data):
    """
    data frame from list
    """
    if isinstance(data, list):
        column_names = sorted(
            set(sum([list(data_item.columns) for data_item in data], [])))
        # ensure all are properly aligned
        # note we don't check that all the columns match here
        data = [data_item[column_names] for data_item in data]

        # add on an offset
        for (offset_value, data_item) in enumerate(data):
            data_item.index = data_item.index + \
                pd.Timedelta("%ds" % offset_value)

        # pooled
        # stack everything up
        data = pd.concat(data, axis=0)
        data = data.sort_index()

    return data


def must_haves_from_list(data):
    must_haves_list = [must_have_item(data_item)
                       for data_item in data]
    must_haves = list(set(sum(must_haves_list, [])))

    return must_haves


def must_have_item(slice_data):
    """
    Returns the columns of slice_data for which we have at least one non nan value

    :param slice_data: Data to get correlations from
    :type slice_data: pd.DataFrame

    :returns: list of bool

    >>>
    """

    def _any_data(xseries):
        data_present = [not np.isnan(x) for x in xseries]

        return any(data_present)

    some_data = slice_data.apply(_any_data, axis=0)
    some_data_flags = list(some_data.values)

    return some_data_flags


def pd_readcsv_frompackage(filename):
    """
    Run pd_readcsv on a file in python

    :param args: List showing location in project directory of file eg systems, provided, tests.csv
    :type args: str

    :returns: pd.DataFrame

    """

    full_filename = get_filename_for_package(filename)
    return pd_readcsv(full_filename)


def pd_readcsv(filename, date_index_name="DATETIME"):
    """
    Reads a pandas data frame, with time index labelled
    package_name(/path1/path2.., filename

    :param filename: Filename with extension
    :type filename: str

    :param date_index_name: Column name of date index
    :type date_index_name: list of str


    :returns: pd.DataFrame

    """

    ans = pd.read_csv(filename)
    ans.index = pd.to_datetime(ans[date_index_name]).values

    del ans[date_index_name]

    ans.index.name = None

    return ans


def apply_cap(pd_series, capvalue):
    """
    Applies a cap to the values in a Tx1 pandas series

    :param pd_series: Tx1 pandas series
    :type pd_dataframe: pd.Series

    :param capvalue: Maximum absolute value allowed
    :type capvlue: int or float


    :returns: pd.DataFrame Tx1

    >>> x=pd.Series([2.0, 7.0, -7.0, -6.99], pd.date_range(pd.datetime(2015,1,1), periods=4))
    >>> apply_cap(x, 5.0)
    2015-01-01  2
    2015-01-02  5
    2015-01-03 -5
    2015-01-04 -5
    Freq: D, dtype: float64
    """
    # Will do weird things otherwise
    assert capvalue > 0

    # create max and min columns
    max_ts = pd.Series([capvalue] * len(pd_series), pd_series.index)
    min_ts = pd.Series([-capvalue] * len(pd_series), pd_series.index)

    joined_ts = pd.concat([pd_series, max_ts], axis=1)
    joined_ts = joined_ts.min(axis=1)
    joined_ts = pd.concat([joined_ts, min_ts], axis=1)
    joined_ts = joined_ts.max(axis=1)

    joined_ts[np.isnan(pd_series)] = np.nan
    return joined_ts


def fix_weights_vs_pdm(weights, pdm):
    """
    Take a matrix of weights and positions/forecasts (pdm)

    Ensure that the weights in each row add up to 1, for active positions/forecasts (not np.nan values after forward filling)

    This deals with the problem of different rules and/or instruments having different history

    :param weights: Weights to
    :type weights: TxK pd.DataFrame (same columns as weights, perhaps different length)

    :param pdm:
    :type pdm: TxK pd.DataFrame (same columns as weights, perhaps different length)

    :returns: TxK pd.DataFrame of adjusted weights

    """

    # forward fill forecasts/positions
    pdm_ffill = pdm.ffill()

    adj_weights = uniquets(weights)

    # resample weights
    adj_weights = adj_weights.reindex(pdm_ffill.index, method='ffill')

    # ensure columns are aligned
    adj_weights = adj_weights[pdm.columns]

    # remove weights if nan forecast
    adj_weights[np.isnan(pdm_ffill)] = 0.0

    # change rows so weights add to one
    def _sum_row_fix(weight_row):
        swr = sum(weight_row)
        if swr == 0.0:
            return weight_row
        new_weights = weight_row / swr
        return new_weights

    adj_weights = adj_weights.apply(_sum_row_fix, 1)

    return adj_weights


def drawdown(x):
    """
    Returns a ts of drawdowns for a time series x

    :param x: account curve (cumulated returns)
    :param x: pd.DataFrame or Series

    :returns: pd.DataFrame or Series

    """
    maxx = x.expanding(min_periods=1).max()
    return x - maxx


if __name__ == '__main__':
    import doctest
    doctest.testmod()
