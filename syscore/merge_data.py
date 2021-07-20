## Merge series together
from copy import copy
import pandas as pd
import datetime

from syscore.dateutils import SECONDS_PER_DAY
from syscore.objects import arg_not_supplied, named_object
from sysdata.config.production_config import get_production_config

class mergeStatus(object):
    def __init__(self, text):
        self._text = text

    def __repr__(self):
        return self._text

status_old_data = mergeStatus("Only_Old_data")
status_new_data = mergeStatus("Only_New_data")
status_merged_data = mergeStatus("Merged_data")

no_spike = object()
spike_in_data = object()

class mergingDataWithStatus(object):
    def __init__(self, status: mergeStatus,
                 first_date: datetime.datetime,
                 merged_data: pd.DataFrame):
        self._status = status
        self._first_date = first_date
        self._merged_data = merged_data

    @property
    def status(self):
        return self._status

    @property
    def first_date(self):
        return self._first_date

    @property
    def merged_data(self):
        return self._merged_data

    @classmethod
    def only_old_data(mergingDataWithStatus, old_data):
        return mergingDataWithStatus(status_old_data, None, old_data)

    @classmethod
    def only_new_data(mergingDataWithStatus, new_data):
        return mergingDataWithStatus(status_new_data, None, new_data)

    @property
    def spike_present(self) -> bool:
        spike_date = self.date_of_spike
        if spike_date is no_spike:
            return False
        else:
            return True

    @property
    def date_of_spike(self):
        spike_date = getattr(self, "_spike_date", no_spike)
        return spike_date

    def add_spike_date(self, spike_date: datetime.datetime):
        self._spike_date = spike_date

def merge_newer_data(
    old_data, new_data,
        check_for_spike=True, column_to_check=arg_not_supplied
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
    merged_data_with_status = merge_newer_data_no_checks(
        old_data, new_data)

    # check for spike
    if check_for_spike:
        merged_data_with_status = spike_check_merged_data(
           merged_data_with_status,
            column_to_check=column_to_check,
        )
        if merged_data_with_status.spike_present:
            return spike_in_data

    merged_data = merged_data_with_status.merged_data

    return merged_data

def merge_newer_data_no_checks(old_data, new_data)-> mergingDataWithStatus:
    """
    Merge new data, with old data. Any new data that is older than the newest old data will be ignored

    Also returns status and possibly date of merge

    :param old_data: pd.Series or DataFrame
    :param new_data: pd.Series or DataFrame

    :return:  status ,last_date_in_old_data: datetime.datetime, merged_data: pd.Series or DataFrame
    """

    if len(new_data.index) == 0:
        return mergingDataWithStatus.only_old_data(old_data)
    if len(old_data.index) == 0:
        return mergingDataWithStatus.only_new_data(new_data)


    merged_data_with_status = _merge_newer_data_no_checks_if_both_old_and_new(old_data, new_data)

    return merged_data_with_status


def _merge_newer_data_no_checks_if_both_old_and_new(old_data, new_data)-> mergingDataWithStatus:

    last_date_in_old_data = old_data.index[-1]
    new_data.sort_index()
    actually_new_data = new_data[new_data.index > last_date_in_old_data]

    if len(actually_new_data) == 0:
        # No additional data
        return mergingDataWithStatus.only_old_data(old_data)

    first_date_in_new_data = actually_new_data.index[0]

    merged_data = pd.concat([old_data, actually_new_data], axis=0)
    merged_data = merged_data.sort_index()

    # remove duplicates (shouldn't be any, but...)
    merged_data = merged_data[~merged_data.index.duplicated(keep="first")]

    return mergingDataWithStatus(status_merged_data, first_date_in_new_data, merged_data)


def spike_check_merged_data(
        merged_data_with_status: mergingDataWithStatus,
        column_to_check=arg_not_supplied) -> mergingDataWithStatus:

    merge_status = merged_data_with_status.status
    merged_data = merged_data_with_status.merged_data

    if merge_status is status_old_data:
        # No checking, just old data
        return merged_data_with_status

    if merge_status is status_new_data:
        # check everything as there is no old data
        first_date_in_new_data = None
    else:
        first_date_in_new_data = merged_data_with_status.first_date

    spike_date = _first_spike_in_data(
        merged_data, first_date_in_new_data, column_to_check=column_to_check
    )

    merged_data_with_status.add_spike_date(spike_date)

    return merged_data_with_status



def _first_spike_in_data(
    merged_data, first_date_in_new_data=None, column_to_check=arg_not_supplied
):
    """
    Checks to see if any data after last_date_in_old_data has spikes

    :param merged_data:
    :return: date if spike, else None
    """
    data_to_check = _get_data_to_check(merged_data, column_to_check=column_to_check)
    change_in_avg_units = _calculate_change_in_avg_units(data_to_check)
    change_in_avg_units_to_check = _get_change_in_avg_units_to_check(change_in_avg_units, first_date_in_new_data = first_date_in_new_data)

    first_spike = _check_for_spikes_in_change_in_avg_units(change_in_avg_units_to_check)

    return first_spike

def _get_data_to_check(merged_data, column_to_check = arg_not_supplied):
    col_list = getattr(merged_data, "columns", None)
    if col_list is None:
        # already a series
        data_to_check = merged_data
    else:
        if column_to_check is arg_not_supplied:
            column_to_check = col_list[0]
        data_to_check = merged_data[column_to_check]

    return data_to_check

def _calculate_change_in_avg_units(data_to_check: pd.Series) -> pd.Series:

    # Calculate the average change per day
    change_pd = average_change_per_day(data_to_check)

    # absolute is what matters
    abs_change_pd = change_pd.abs()

    # hard to know what span to use here as could be daily, intraday or a
    # mixture
    avg_abs_change = abs_change_pd.ewm(span=500).mean()

    change_in_avg_units = abs_change_pd / avg_abs_change

    return change_in_avg_units

def average_change_per_day(data_to_check: pd.Series) -> pd.Series:
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


def _get_change_in_avg_units_to_check(change_in_avg_units: pd.Series, first_date_in_new_data = None):
    if first_date_in_new_data is None:
        # No merged data so we check it all
        change_in_avg_units_to_check = change_in_avg_units
    else:
        # just check more recent data
        change_in_avg_units_to_check = change_in_avg_units[first_date_in_new_data:]

    return change_in_avg_units_to_check

production_config = get_production_config()
max_spike = production_config.max_price_spike


def _check_for_spikes_in_change_in_avg_units(change_in_avg_units_to_check: pd.Series):

    if any(change_in_avg_units_to_check > max_spike):
        first_spike=change_in_avg_units_to_check.index[change_in_avg_units_to_check > max_spike][0]
    else:
        first_spike = no_spike

    return first_spike

def full_merge_of_existing_data(old_data, new_data, 
    check_for_spike=False, column_to_check=arg_not_supplied, keep_older:bool=True):
    """
    Merges old data with new data.
    Any Nan in the existing data will be replaced (be careful!)

    :param old_data: pd.DataFrame
    :param new_data: pd.DataFrame
    :param check_for_spike: bool
    :param column_to_check: column name to check for spike
    :param keep_older: bool. Keep older data (default)

    :returns: pd.DataFrame
    """
    merged_data_with_status = full_merge_of_existing_data_no_checks(old_data, new_data,
        keep_older=keep_older)

    # check for spike
    if check_for_spike:
        merged_data_with_status = spike_check_merged_data(
            merged_data_with_status,
            column_to_check=column_to_check,
        )
        if merged_data_with_status.spike_present:
            return spike_in_data

    return merged_data_with_status.merged_data


def full_merge_of_existing_data_no_checks(old_data, new_data, 
    keep_older:bool=True) -> mergingDataWithStatus: 
    """
    Merges old data with new data.
    Any Nan in the existing data will be replaced (be careful!)

    :param old_data: pd.DataFrame
    :param new_data: pd.DataFrame
    :param keep_older: bool. Keep older data (default)

    :returns: mergingDataWithStatus
    """
    if len(old_data.index) == 0:
        return mergingDataWithStatus.only_new_data(new_data)
    if len(new_data.index) == 0:
        return mergingDataWithStatus.only_old_data(old_data)

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

        merged_series = full_merge_of_existing_series(old_series, new_series, keep_older)

        merged_data[colname] = merged_series

    merged_data_as_df = pd.DataFrame(merged_data)
    merged_data_as_df = merged_data_as_df.sort_index()

    # get the difference between merged dataset and old one to get the earliest change
    actually_new_data = pd.concat([merged_data_as_df, old_data]).drop_duplicates(keep=False)

    if len(actually_new_data.index) == 0:
        return mergingDataWithStatus.only_old_data(old_data)

    first_date_in_new_data = actually_new_data.index[0]

    return mergingDataWithStatus(status_merged_data, first_date_in_new_data, merged_data_as_df)


def full_merge_of_existing_series(old_series, new_series, keep_older:bool=True):
    """
    Merges old data with new data.
    Any Nan in the existing data will be replaced (be careful!)

    :param old_data: pd.Series
    :param new_data: pd.Series
    :param keep_older: bool. Keep older data (default)

    :returns: pd.Series
    """
    if len(old_series) == 0:
        return new_series
    if len(new_series) == 0:
        return old_series

    if keep_older:
        joint_data = pd.concat([old_series, new_series], axis=1)
        joint_data.columns = ["original", "new"]

        # fill to the left
        joint_data_filled_across = joint_data.bfill(1)
        merged_data = joint_data_filled_across["original"]
    else:
        # update older data with non-NA values from new data series
        merged_data = old_series.copy()
        merged_data.update(new_series)

    return merged_data


all_labels_match = named_object("all labels match")
mismatch_on_last_day = named_object("mismatch_on_last_day")
original_index_matches_new = named_object("original index matches new")


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
