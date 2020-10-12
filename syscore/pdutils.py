"""
Utilities to help with pandas
"""

import pandas as pd
import datetime

import numpy as np
from copy import copy

from syscore.fileutils import get_filename_for_package
from syscore.dateutils import (
    BUSINESS_DAYS_IN_YEAR,
    time_matches,
    CALENDAR_DAYS_IN_YEAR,
    SECONDS_PER_DAY,
    NOTIONAL_CLOSING_TIME_AS_PD_OFFSET

)
from syscore.objects import _named_object, data_error, arg_not_supplied
from sysdata.private_config import get_private_then_default_key_value

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


def pd_readcsv_frompackage(filename):
    """
    Run pd_readcsv on a file in python

    :param args: List showing location in project directory of file eg systems,
      provided, tests.csv
    :type args: str

    :returns: pd.DataFrame

    """

    full_filename = get_filename_for_package(filename)
    return pd_readcsv(full_filename)


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
    adj_weights = adj_weights.reindex(pdm_ffill.index, method="ffill")

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
    :type x: pd.DataFrame or Series

    :returns: pd.DataFrame or Series

    """
    maxx = x.expanding(min_periods=1).max()
    return x - maxx


def from_dict_of_values_to_df(data_dict, ts_index, columns=None):
    """
    Turn a set of fixed values into a pd.dataframe

    :param data_dict: A dict of scalars
    :param ts_index: A timeseries index
    :param columns: (optional) A list of str to align the column names to [must have entries in data_dict keys]
    :return: pd.dataframe, column names from data_dict, values repeated scalars
    """

    if columns is None:
        columns = data_dict.keys()

    columns_as_list = list(columns)

    numeric_values = dict(
        [(keyname, [data_dict[keyname]] * len(ts_index)) for keyname in columns_as_list]
    )

    pd_dataframe = pd.DataFrame(numeric_values, ts_index)

    return pd_dataframe


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


status_old_data = object()
status_new_data = object()
status_merged_data = object()


def merge_newer_data(
    old_data, new_data, check_for_spike=True, column_to_check=arg_not_supplied
):
    """
    Merge new data, with old data. Any new data that is older than the newest old data will be ignored

    If check_for_spike will return data_error if price moves too much on join point

    :param old_data: pd.Series or DataFrame
    :param new_data: pd.Series or DataFrame
    :param check_for_spike: bool
    :param column_to_check: column name to check for spike

    :return:  pd.Series or DataFrame
    """
    merge_status, first_date_in_new_data, merged_data = merge_newer_data_no_checks(
        old_data, new_data)

    # check for spike
    if check_for_spike:
        spike_present, _ = spike_check_merged_data(
            merge_status,
            first_date_in_new_data,
            merged_data,
            column_to_check=column_to_check,
        )
        if spike_present:
            return data_error

    return merged_data


def spike_check_merged_data(
        merge_status,
        first_date_in_new_data,
        merged_data,
        column_to_check=arg_not_supplied):
    if merge_status is status_old_data:
        # No checking
        return False, None

    if merge_status is status_new_data:
        # check everything
        first_date_in_new_data = None

    spike_present, spike_date = _check_for_spike_in_data(
        merged_data, first_date_in_new_data, column_to_check=column_to_check
    )

    return spike_present, spike_date


def merge_newer_data_no_checks(old_data, new_data):
    """
    Merge new data, with old data. Any new data that is older than the newest old data will be ignored

    Also returns status and possibly date of merge

    :param old_data: pd.Series or DataFrame
    :param new_data: pd.Series or DataFrame

    :return:  status ,last_date_in_old_data: datetime.datetime, merged_data: pd.Series or DataFrame
    """
    if len(old_data.index) == 0:
        return status_new_data, None, new_data
    if len(new_data.index) == 0:
        return status_old_data, None, old_data

    last_date_in_old_data = old_data.index[-1]
    new_data.sort_index()
    actually_new_data = new_data[new_data.index > last_date_in_old_data]

    if len(actually_new_data) == 0:
        # No additional data
        return status_old_data, None, old_data

    first_date_in_new_data = actually_new_data.index[0]

    merged_data = pd.concat([old_data, actually_new_data], axis=0)
    merged_data = merged_data.sort_index()

    # remove duplicates (shouldn't be any, but...)
    merged_data = merged_data[~merged_data.index.duplicated(keep="first")]

    return status_merged_data, first_date_in_new_data, merged_data


def _check_for_spike_in_data(
    merged_data, first_date_in_new_data=None, column_to_check=arg_not_supplied
):
    # Returns tuple bool, logical date of spike (or None)
    first_spike = _first_spike_in_data(
        merged_data, first_date_in_new_data, column_to_check=column_to_check
    )

    if first_spike is None:
        spike_exists = False
    else:
        spike_exists = True

    return spike_exists, first_spike


def _first_spike_in_data(
    merged_data, first_date_in_new_data=None, column_to_check=arg_not_supplied
):
    """
    Checks to see if any data after last_date_in_old_data has spikes

    :param merged_data:
    :return: date if spike, else None
    """
    max_spike = get_private_then_default_key_value("max_price_spike")
    col_list = getattr(merged_data, "columns", None)
    if col_list is None:
        # already a series
        data_to_check = merged_data
    else:
        if column_to_check is arg_not_supplied:
            column_to_check = col_list[0]
        data_to_check = merged_data[column_to_check]

    # Calculate the average change per day
    change_pd = average_change_per_day(data_to_check)

    # absolute is what matters
    abs_change_pd = change_pd.abs()
    # hard to know what span to use here as could be daily, intraday or a
    # mixture
    avg_abs_change = abs_change_pd.ewm(span=500).mean()

    change_in_avg_units = abs_change_pd / avg_abs_change

    if first_date_in_new_data is None:
        # No merged data so we check it all
        data_to_check = change_in_avg_units
    else:
        data_to_check = change_in_avg_units[first_date_in_new_data:]

    if any(data_to_check > max_spike):
        return data_to_check.index[data_to_check > max_spike][0]
    else:
        return None


def average_change_per_day(data_to_check):
    data_diff = data_to_check.diff()[1:]
    index_diff = data_to_check.index[1:] - data_to_check.index[:-1]
    index_diff_days = [
        diff.total_seconds() /
        SECONDS_PER_DAY for diff in index_diff]

    change_per_day = [
        diff / (diff_days ** 0.5)
        for diff, diff_days in zip(data_diff.values, index_diff_days)
    ]

    change_pd = pd.Series(change_per_day, index=data_to_check.index[1:])

    return change_pd


def full_merge_of_existing_data(old_data, new_data):
    """
    Merges old data with new data.
    Any Nan in the existing data will be replaced (be careful!)

    :param old_data: pd.DataFrame
    :param new_data: pd.DataFrame

    :returns: pd.DataFrame
    """

    old_columns = old_data.columns
    merged_data = {}
    for colname in old_columns:
        old_series = copy(old_data[colname])
        try:
            new_series = copy(new_data[colname])
        except KeyError:
            # missing from new data, so we just take the old
            merged_data[colname] = old_data
            continue

        merged_series = full_merge_of_existing_series(old_series, new_series)

        merged_data[colname] = merged_series

    merged_data_as_df = pd.DataFrame(merged_data)
    merged_data_as_df = merged_data_as_df.sort_index()

    return merged_data_as_df


def full_merge_of_existing_series(old_series, new_series):
    """
    Merges old data with new data.
    Any Nan in the existing data will be replaced (be careful!)

    :param old_data: pd.Series
    :param new_data: pd.Series

    :returns: pd.Series
    """
    if len(old_series) == 0:
        return new_series
    if len(new_series) == 0:
        return old_series

    joint_data = pd.concat([old_series, new_series], axis=1)
    joint_data.columns = ["original", "new"]

    # fill to the left
    joint_data_filled_across = joint_data.bfill(1)
    merged_data = joint_data_filled_across["original"]

    return merged_data


all_labels_match = _named_object("all labels match")
mismatch_on_last_day = _named_object("mismatch_on_last_day")
original_index_matches_new = _named_object("original index matches new")


def merge_data_series_with_label_column(
    original_data, new_data, col_names=dict(
        data="PRICE", label="PRICE_CONTRACT")):
    """
    For two pd.DataFrames with 2 columns, including a label column, update the data when the labels
      start consistently matching

    >>> s1=pd.DataFrame(dict(PRICE=[1,2,3,np.nan], PRICE_CONTRACT = ["a", "a", "b", "b"]), index=['a1','a2','a3','a4'])
    >>> s2=pd.DataFrame(dict(PRICE=[  7,3,4], PRICE_CONTRACT = [          "b", "b", "b"]), index=['a2','a3','a4'])
    >>> merge_data_series_with_label_column(s1,s2)
        PRICE PRICE_CONTRACT
    a1    1.0              a
    a2    2.0              a
    a3    3.0              b
    a4    4.0              b
    >>> s2=pd.DataFrame(dict(PRICE=[  2,5,4], PRICE_CONTRACT = [          "b", "b", "b"]), index=['a2','a3','a4'])
    >>> merge_data_series_with_label_column(s1,s2)
        PRICE PRICE_CONTRACT
    a1    1.0              a
    a2    2.0              a
    a3    3.0              b
    a4    4.0              b
    >>> s2=pd.DataFrame(dict(PRICE=[  2,3,np.nan], PRICE_CONTRACT = [          "b", "b", "b"]), index=['a2','a3','a4'])
    >>> merge_data_series_with_label_column(s1,s2)
        PRICE PRICE_CONTRACT
    a1    1.0              a
    a2    2.0              a
    a3    3.0              b
    a4    NaN              b
    >>> s1=pd.DataFrame(dict(PRICE=[1,np.nan,3,np.nan], PRICE_CONTRACT = ["a", "a", "b", "b"]), index=['a1','a2','a3','a4'])
    >>> s2=pd.DataFrame(dict(PRICE=[  2,     3,4], PRICE_CONTRACT = [      "a", "b", "b"]), index=['a2','a3','a4'])
    >>> merge_data_series_with_label_column(s1,s2)
        PRICE PRICE_CONTRACT
    a1    1.0              a
    a2    2.0              a
    a3    3.0              b
    a4    4.0              b
    >>> s1=pd.DataFrame(dict(PRICE=[1,np.nan,np.nan], PRICE_CONTRACT = ["a", "a", "b"]), index=['a1','a2','a3'])
    >>> s2=pd.DataFrame(dict(PRICE=[  2,     3,4], PRICE_CONTRACT = [      "b", "b", "b"]), index=['a2','a3','a4'])
    >>> merge_data_series_with_label_column(s1,s2)
        PRICE PRICE_CONTRACT
    a1    1.0              a
    a2    NaN              a
    a3    3.0              b
    a4    4.0              b
    >>> s2=pd.DataFrame(dict(PRICE=[  2,     3,4], PRICE_CONTRACT = [      "b", "c", "c"]), index=['a2','a3','a4'])
    >>> merge_data_series_with_label_column(s1,s2)
        PRICE PRICE_CONTRACT
    a1    1.0              a
    a2    NaN              a
    a3    NaN              b


    :param original_data: a pd.DataFrame with two columns, equal to col_names
    :param new_data: a pd.DataFrame with the same two columns
    :param col_names: dict of str
    :return: pd.DataFrame with two columns
    """

    if len(new_data) == 0:
        return original_data

    if len(original_data) == 0:
        return new_data

    # From the date after this, can happily merge new and old data
    match_data = find_dates_when_label_changes(
        original_data, new_data, col_names=col_names
    )

    if match_data is mismatch_on_last_day:
        # No matching is possible
        return original_data
    elif match_data is original_index_matches_new:
        first_date_after_series_mismatch = original_data.index[0]
        last_date_when_series_mismatch = original_index_matches_new
    else:
        first_date_after_series_mismatch, last_date_when_series_mismatch = match_data

    # Concat the two price series together, fill to the left
    # This will replace any NA values in existing prices with new ones
    label_column = col_names["label"]
    data_column = col_names["data"]

    merged_data = full_merge_of_existing_series(
        original_data[data_column][first_date_after_series_mismatch:],
        new_data[data_column][first_date_after_series_mismatch:],
    )

    labels_in_new_data = new_data[last_date_when_series_mismatch:][label_column]
    labels_in_old_data = original_data[:
                                       first_date_after_series_mismatch][label_column]
    labels_in_merged_data = pd.concat(
        [labels_in_old_data, labels_in_new_data], axis=0)
    labels_in_merged_data = labels_in_merged_data.loc[
        ~labels_in_merged_data.index.duplicated(keep="first")
    ]
    labels_in_merged_data_reindexed = labels_in_merged_data.reindex(
        merged_data.index)

    labelled_merged_data = pd.concat(
        [labels_in_merged_data_reindexed, merged_data], axis=1
    )
    labelled_merged_data.columns = [label_column, data_column]

    # for older data, keep older data
    if last_date_when_series_mismatch is original_index_matches_new:
        current_and_merged_data = labelled_merged_data
    else:
        original_data_to_use = original_data[:last_date_when_series_mismatch]

        # Merged data is the old data, and then the new data
        current_and_merged_data = pd.concat(
            [original_data_to_use, labelled_merged_data], axis=0
        )

    return current_and_merged_data


def find_dates_when_label_changes(
    original_data,
    new_data,
    col_names=dict(
        data="PRICE",
        label="PRICE_CONTRACT")):
    """
    For two pd.DataFrames with 2 columns, including a label column, find the date after which the labelling
     is consistent across columns

    >>> s1=pd.DataFrame(dict(PRICE=[1,2,3,np.nan], PRICE_CONTRACT = ["a", "a", "b", "b"]), index=['a1','a2','a3','a4'])
    >>> s2=pd.DataFrame(dict(PRICE=[  2,3,4], PRICE_CONTRACT = [          "b", "b", "b"]), index=['a2','a3','a4'])
    >>> find_dates_when_label_changes(s1, s2)
    ('a3', 'a2')
    >>> s2=pd.DataFrame(dict(PRICE=[  2,3,4], PRICE_CONTRACT = [          "a", "b", "b"]), index=['a2','a3','a4'])
    >>> find_dates_when_label_changes(s1, s2)
    ('a2', 'a1')
    >>> s2=pd.DataFrame(dict(PRICE=[  2,3,4], PRICE_CONTRACT = [          "c", "c", "c"]), index=['a2','a3','a4'])
    >>> find_dates_when_label_changes(s1, s2)
    mismatch_on_last_day
    >>> find_dates_when_label_changes(s1, s1)
    original index matches new
    >>> s2=pd.DataFrame(dict(PRICE=[1, 2,3,4], PRICE_CONTRACT = ["a","c", "c", "c"]), index=['a1','a2','a3','a4'])
    >>> find_dates_when_label_changes(s1, s2)
    mismatch_on_last_day

    :param original_data: some data
    :param new_data: some new data
    :param col_names: dict of str
    :return: tuple or object if match didn't work out
    """
    label_column = col_names["label"]

    joint_labels = pd.concat(
        [original_data[label_column], new_data[label_column]], axis=1
    )
    joint_labels.columns = ["current", "new"]
    joint_labels = joint_labels.sort_index()

    new_data_start = new_data.index[0]

    existing_labels_in_new_period = joint_labels["current"][new_data_start:].ffill(
    )
    new_labels_in_new_period = joint_labels["new"][new_data_start:].ffill()

    # Find the last date when the labels didn't match, and the first date
    # after that
    match_data = find_dates_when_series_starts_matching(
        existing_labels_in_new_period, new_labels_in_new_period
    )

    if match_data is mismatch_on_last_day:
        # Can't use any of new data
        return mismatch_on_last_day

    elif match_data is all_labels_match:
        # Can use entire series becuase all match
        if new_data.index[0] == original_data.index[0]:
            # They are same size, so have to use whole of original data
            return original_index_matches_new
        else:
            # All the new data matches
            first_date_after_series_mismatch = new_data_start
            last_date_when_series_mismatch = original_data.index[
                original_data.index < new_data_start
            ][-1]
    else:
        first_date_after_series_mismatch, last_date_when_series_mismatch = match_data

    return first_date_after_series_mismatch, last_date_when_series_mismatch


def find_dates_when_series_starts_matching(series1, series2):
    """
    Find the last index value when series1 and series 2 didn't match, and the next index after that

    series must be matched for index and same length

    >>> s1=pd.Series(["a", "b", "b", "b"], index=[1,2,3,4])
    >>> s2=pd.Series(["c", "b", "b", "b"], index=[1,2,3,4])
    >>> find_dates_when_series_starts_matching(s1, s2)
    (2, 1)
    >>> s2=pd.Series(["a", "a", "b", "b"], index=[1,2,3,4])
    >>> find_dates_when_series_starts_matching(s1, s2)
    (3, 2)
    >>> s2=pd.Series(["a", "b", "a", "b"], index=[1,2,3,4])
    >>> find_dates_when_series_starts_matching(s1, s2)
    (4, 3)
    >>> s2=pd.Series(["a", "b", "b", "b"], index=[1,2,3,4])
    >>> find_dates_when_series_starts_matching(s1, s2)
    all labels match
    >>> s2=pd.Series(["a", "b", "b", "c"], index=[1,2,3,4])
    >>> find_dates_when_series_starts_matching(s1, s2)
    mismatch_on_last_day

    :param series1: pd.Series
    :param series2: pd.Series
    :return: 2-tuple of index values
    """

    # Data is same length, and timestamp matched, so equality of values is
    # sufficient
    period_equal = [x == y for x, y in zip(series1.values, series2.values)]

    if all(period_equal):
        return all_labels_match

    if not period_equal[-1]:
        return mismatch_on_last_day

    # Want last False value
    period_equal.reverse()
    first_false_in_reversed_list = period_equal.index(False)

    last_true_before_first_false_in_reversed_list = first_false_in_reversed_list - 1

    reversed_time_index = series1.index[::-1]
    last_true_before_first_false_in_reversed_list_date = reversed_time_index[
        last_true_before_first_false_in_reversed_list
    ]
    first_false_in_reversed_list_date = reversed_time_index[
        first_false_in_reversed_list
    ]

    first_date_after_series_mismatch = (
        last_true_before_first_false_in_reversed_list_date
    )
    last_date_when_series_mismatch = first_false_in_reversed_list_date

    return first_date_after_series_mismatch, last_date_when_series_mismatch


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

if __name__ == "__main__":
    import doctest

    doctest.testmod()
