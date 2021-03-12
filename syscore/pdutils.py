"""
Utilities to help with pandas
"""
import pandas as pd
import datetime

import numpy as np
from copy import copy

from syscore.dateutils import (
    BUSINESS_DAYS_IN_YEAR,
    time_matches,
    CALENDAR_DAYS_IN_YEAR,
    NOTIONAL_CLOSING_TIME_AS_PD_OFFSET

)

DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def turnover(x, y):
    """
    Gives the turnover of x, once normalised for y

    Returned in annualised terms

    Assumes both x and y are daily business days
    """

    if isinstance(y, float) or isinstance(y, int):
        y = pd.Series([float(y)] * len(x.index), x.index)

    norm_x = x / y.ffill()

    avg_daily = float(norm_x.diff().abs().resample("1B").sum().mean())

    return avg_daily * BUSINESS_DAYS_IN_YEAR


def uniquets(x):
    """
    Makes x unique
    """
    x = x.groupby(level=0).last()
    return x


def df_from_list(data):
    """
    Create a single data frame from list of data frames

    To preserve a unique time signature we add on 1..2..3... micro seconds to successive elements of the list

    WARNING: SO THIS METHOD WON'T WORK WITH HIGH FREQUENCY DATA!

    THIS WILL ALSO DESTROY ANY AUTOCORRELATION PROPERTIES
    """
    if isinstance(data, list):
        column_names = sorted(
            set(sum([list(data_item.columns) for data_item in data], []))
        )
        # ensure all are properly aligned
        # note we don't check that all the columns match here
        new_data = [data_item[column_names] for data_item in data]

        # add on an offset
        for (offset_value, data_item) in enumerate(new_data):
            data_item.index = data_item.index + \
                pd.Timedelta("%dus" % offset_value)

        # pooled
        # stack everything up
        new_data = pd.concat(new_data, axis=0)
        new_data = new_data.sort_index()
    else:
        # nothing to do here
        new_data = copy(data)

    return new_data


def must_haves_from_list(data):
    must_haves_list = [must_have_item(data_item) for data_item in data]
    must_haves = list(set(sum(must_haves_list, [])))

    return must_haves


def must_have_item(slice_data):
    """
    Returns the columns of slice_data for which we have at least one non nan value

    :param slice_data: simData to get correlations from
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



def pd_readcsv(
    filename,
    date_index_name="DATETIME",
    date_format=DEFAULT_DATE_FORMAT,
    input_column_mapping=None,
    skiprows=0,
    skipfooter=0,
):
    """
    Reads a pandas data frame, with time index labelled
    package_name(/path1/path2.., filename

    :param filename: Filename with extension
    :type filename: str

    :param date_index_name: Column name of date index
    :type date_index_name: list of str

    :param date_format: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
    :type date_format: str

    :param input_column_mapping: If supplied remaps column names in .csv file
    :type input_column_mapping: dict or None

    :param skiprows, skipfooter: passed to pd.read_csv

    :returns: pd.DataFrame

    """

    ans = pd.read_csv(filename, skiprows=skiprows, skipfooter=skipfooter)
    ans.index = pd.to_datetime(ans[date_index_name], format=date_format).values

    del ans[date_index_name]

    ans.index.name = None

    if input_column_mapping is None:
        return ans

    # Have to remap
    new_ans = pd.DataFrame(index=ans.index)
    for new_col_name, old_col_name in input_column_mapping.items():
        new_ans[new_col_name] = ans[old_col_name]

    return new_ans


def fix_weights_vs_position_or_forecast(weights: pd.DataFrame,
                                        position_or_forecast: pd.DataFrame):
    """
    Take a matrix of weights and positions/forecasts (pdm)

    Ensure that the weights in each row add up to 1, for active positions/forecasts (not np.nan values after forward filling)

    This deals with the problem of different rules and/or instruments having different history

    :param weights: Weights to
    :type weights: TxK pd.DataFrame (same columns as weights, perhaps different length)

    :param position_or_forecast:
    :type position_or_forecast: TxK pd.DataFrame (same columns as weights, perhaps different length)

    :returns: TxK pd.DataFrame of adjusted weights

    """

    # forward fill forecasts/positions
    pdm_ffill = position_or_forecast.ffill()

    # resample weights
    adj_weights = uniquets(weights)
    adj_weights = adj_weights.reindex(pdm_ffill.index, method="ffill")

    # ensure columns are aligned
    adj_weights = adj_weights[position_or_forecast.columns]

    # remove weights if nan forecast or position
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
    :type x: pd.DataFrame or Series

    :returns: pd.DataFrame or Series

    """
    maxx = x.expanding(min_periods=1).max()
    return x - maxx


def from_dict_of_values_to_df(data_dict: dict, long_ts_index, columns: list=None):
    """
    Turn a set of fixed values into a pd.dataframe that spans the long index

    :param data_dict: A dict of scalars
    :param ts_index: A timeseries index
    :param columns: (optional) A list of str to align the column names to [must have entries in data_dict keys]
    :return: pd.dataframe, column names from data_dict, values repeated scalars
    """

    if columns is None:
        columns = data_dict.keys()

    columns_as_list = list(columns)

    ts_index = [long_ts_index[0], long_ts_index[1]]

    numeric_values = dict(
        [(keyname, [data_dict[keyname]] * len(ts_index)) for keyname in columns_as_list]
    )

    pd_dataframe = pd.DataFrame(numeric_values, ts_index)

    return pd_dataframe



def from_scalar_values_to_ts(scalar_value: float, long_ts_index) -> pd.Series:
    """
    Turn a set of fixed values into a pd.dataframe that spans the long index

    :param data_dict: A dict of scalars
    :param ts_index: A timeseries index
    :param columns: (optional) A list of str to align the column names to [must have entries in data_dict keys]
    :return: pd.dataframe, column names from data_dict, values repeated scalars
    """

    ts_index = [long_ts_index[0], long_ts_index[1]]

    pd_series = pd.Series([scalar_value]*len(ts_index), index = ts_index)

    return pd_series



def create_arbitrary_pdseries(
    data_list, date_start=datetime.datetime(1980, 1, 1), freq="B"
):
    """
    Return a pandas Series with an arbitrary date index

    :param data_list: simData
    :type data_list: list of floats or ints

    :param date_start: First date to use in index
    :type date_start: datetime

    :param freq: Frequency of date index
    :type freq: str of a type that pd.date_range will recognise

    :returns: pd.Series  (same length as simData)

    >>> create_arbitrary_pdseries([1,2,3])
    1980-01-01    1
    1980-01-02    2
    1980-01-03    3
    Freq: B, dtype: int64
    """

    date_index = pd.date_range(
        start=date_start,
        periods=len(data_list),
        freq=freq)

    pdseries = pd.Series(data_list, index=date_index)

    return pdseries


def dataframe_pad(starting_df, column_list, padwith=0.0):
    """
    Takes a dataframe and adds extra columns if neccessary so we end up with columns named column_list

    :param starting_df: A pd.dataframe with named columns
    :param column_list: A list of column names
    :param padwith: The value to pad missing columns with
    :return: pd.Dataframe
    """

    def _pad_column(column_name, starting_df, padwith):
        if column_name in starting_df.columns:
            return starting_df[column_name]
        else:
            return pd.Series([0.0] * len(starting_df.index), starting_df.index)

    new_data = [_pad_column(column_name, starting_df, padwith)
                for column_name in column_list]

    new_df = pd.concat(new_data, axis=1)
    new_df.columns = column_list

    return new_df


def proportion_pd_object_intraday(
    data, closing_time=NOTIONAL_CLOSING_TIME_AS_PD_OFFSET
):
    """
    Return the proportion of intraday data in a pd.Series or DataFrame

    :param data: the underlying data
    :param closing_time: the time which we are using as a closing time
    :return: float, the proportion of the data.index that matches an intraday timestamp

    So 0 = All daily data, 1= All intraday data
    """

    data_index = data.index
    length_index = len(data_index)

    count_matches = [
        time_matches(index_entry, closing_time) for index_entry in data_index
    ]
    total_matches = sum(count_matches)
    proportion_matching_close = float(total_matches) / float(length_index)
    proportion_intraday = 1 - proportion_matching_close

    return proportion_intraday


def strip_out_intraday(
    data, closing_time=pd.DateOffset(hours=23, minutes=0, seconds=0)
):
    """
    Return a pd.Series or DataFrame with only the times matching closing_time
    Used when we have a mix of daily and intraday data, where the daily data has been given a nominal timestamp

    :param data: pd object
    :param closing_time: pdDateOffset with
    :return: pd object
    """

    data_index = data.index
    length_index = len(data_index)

    daily_matches = [
        time_matches(index_entry, closing_time) for index_entry in data_index
    ]

    return data[daily_matches]


def minimum_many_years_of_data_in_dataframe(data):
    years_of_data_dict = how_many_years_of_data_in_dataframe(data)
    years_of_data_values = years_of_data_dict.values()
    min_years_of_data = min(years_of_data_values)

    return min_years_of_data


def how_many_years_of_data_in_dataframe(data):
    """
    How many years of non NA data do we have?
    Assumes daily timestamp

    :param data: pd.DataFrame with labelled columns
    :return: dict of floats,
    """
    result_dict = dict(data.apply(how_many_years_of_data_in_pd_series, axis=0))

    return result_dict


def how_many_years_of_data_in_pd_series(data_series):
    """
    How many years of actual data do we have
    Assume daily timestamp which is fairly regular

    :param data_series:
    :return: float
    """
    first_valid_date = data_series.first_valid_index()
    last_valid_date = data_series.last_valid_index()

    date_difference = last_valid_date - first_valid_date
    date_difference_days = date_difference.days
    date_difference_years = float(date_difference_days) / CALENDAR_DAYS_IN_YEAR

    return date_difference_years


def check_df_equals(x, y):
    try:
        pd.testing.assert_frame_equal(x, y)
        return True
    except AssertionError:
        return False


def check_ts_equals(x, y):
    try:
        pd.testing.assert_series_equal(x, y, check_names=False)
        return True
    except AssertionError:
        return False


def make_df_from_list_of_named_tuple(tuple_class, list_of_tuples):
    elements = tuple_class._fields
    dict_of_elements = {}
    for element_name in elements:
        this_element_values = [
            getattr(list_entry, element_name) for list_entry in list_of_tuples
        ]
        dict_of_elements[element_name] = this_element_values

    pdf = pd.DataFrame(dict_of_elements)
    pdf.index = pdf[elements[0]]
    pdf = pdf.drop(elements[0], axis=1)

    return pdf


def set_pd_print_options():
    pd.set_option("display.max_rows", 100)
    pd.set_option("display.max_columns", 100)
    pd.set_option("display.width", 1000)


def closing_date_rows_in_pd_object(pd_object):
    return pd_object[
        [time_matches(index_entry, NOTIONAL_CLOSING_TIME_AS_PD_OFFSET) for index_entry in pd_object.index]]

def intraday_date_rows_in_pd_object(pd_object):
    return pd_object[
        [not time_matches(index_entry, NOTIONAL_CLOSING_TIME_AS_PD_OFFSET) for index_entry in pd_object.index]]

def sumup_business_days_over_pd_series_without_double_counting_of_closing_data(pd_series):
    closing_data = closing_date_rows_in_pd_object(pd_series)
    closing_data_summed = closing_data.resample("1B").sum()
    intraday_data = intraday_date_rows_in_pd_object(pd_series)
    intraday_data_summed = intraday_data.resample("1B").sum()
    intraday_data_summed.name = "intraday"
    both_sets_of_data = pd.concat([intraday_data_summed, closing_data_summed], axis=1)
    both_sets_of_data[both_sets_of_data==0] = np.nan
    joint_data = both_sets_of_data.ffill(axis=1)
    joint_data = joint_data.iloc[:,1]

    return joint_data

def replace_all_zeros_with_nan(result: pd.Series) -> pd.Series:
    check_result = copy(result)
    check_result[check_result == 0.0] = np.nan
    if all(check_result.isna()):
        result[:] = np.nan

    return result

if __name__ == "__main__":
    import doctest

    doctest.testmod()
