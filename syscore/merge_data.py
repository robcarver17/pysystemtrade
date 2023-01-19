## Merge series together
import datetime

import pandas as pd
import numpy as np

from copy import copy
from enum import Enum
from typing import Union


from syscore.dateutils import SECONDS_PER_DAY
from syscore.objects import arg_not_supplied, named_object
from syscore.pdutils import is_a_series, is_a_dataframe

VERY_BIG_NUMBER = 99999999.0


def merge_newer_data(
    old_data: Union[pd.Series, pd.DataFrame],
    new_data: Union[pd.Series, pd.DataFrame],
    check_for_spike: bool = True,
    max_spike: float = VERY_BIG_NUMBER,
    column_to_check_for_spike: str = arg_not_supplied,
):
    """
    Merge new data, with old data. Any new data that is older than the newest old data will be ignored
    If check_for_spike will return data_error if price moves too much on join point (checking column_to_check)

    """
    merged_data_with_status = merge_newer_data_no_checks(old_data, new_data)

    # check for spike
    if check_for_spike:
        merged_data_with_status = spike_check_merged_data(
            merged_data_with_status,
            column_to_check_for_spike=column_to_check_for_spike,
            max_spike=max_spike,
        )
        if merged_data_with_status.spike_present:
            return SPIKE_IN_DATA

    merged_data = merged_data_with_status.merged_data

    return merged_data


class mergeStatus(Enum):
    ONLY_OLD = 1
    ONLY_NEW = 2
    MERGED = 3


OLD_DATA_ONLY = mergeStatus.ONLY_OLD
NEW_DATA_ONLY = mergeStatus.ONLY_NEW
MERGED_DATA = mergeStatus.MERGED

NO_SPIKE = named_object("No spike in data")
SPIKE_IN_DATA = named_object("Spike in data")
NO_MERGE_DATE = named_object("No data")


class mergingDataWithStatus(object):
    def __init__(
        self,
        status: mergeStatus,
        date_of_merge_join: Union[datetime.datetime, object],
        merged_data: Union[pd.DataFrame, pd.Series],
    ):
        self._status = status
        self._date_of_merge_join = date_of_merge_join
        self._merged_data = merged_data

    @classmethod
    def only_old_data(cls, old_data):
        return mergingDataWithStatus(
            status=OLD_DATA_ONLY, date_of_merge_join=NO_MERGE_DATE, merged_data=old_data
        )

    @classmethod
    def only_new_data(cls, new_data):
        return mergingDataWithStatus(
            status=NEW_DATA_ONLY, date_of_merge_join=NO_MERGE_DATE, merged_data=new_data
        )

    @property
    def spike_present(self) -> bool:
        spike_date = self.spike_date
        if spike_date is NO_SPIKE:
            return False
        else:
            return True

    @property
    def spike_date(self) -> Union[datetime.datetime, object]:
        spike_date = getattr(self, "_spike_date", NO_SPIKE)
        return spike_date

    @spike_date.setter
    def spike_date(self, spike_date: datetime.datetime):
        self._spike_date = spike_date

    @property
    def status(self) -> mergeStatus:
        return self._status

    @property
    def date_of_merge_join(self) -> Union[datetime.datetime, object]:
        return self._date_of_merge_join

    @property
    def merged_data(self):
        return self._merged_data


def merge_newer_data_no_checks(
    old_data: Union[pd.Series, pd.DataFrame], new_data: Union[pd.Series, pd.DataFrame]
) -> mergingDataWithStatus:
    """
    Merge new data, with old data. Any new data that is older than the newest old data will be ignored

    Also returns status and possibly date of merge

    """

    if len(new_data.index) == 0:
        return mergingDataWithStatus.only_old_data(old_data)
    if len(old_data.index) == 0:
        return mergingDataWithStatus.only_new_data(new_data)

    merged_data_with_status = _merge_newer_data_no_checks_if_both_old_and_new(
        old_data, new_data
    )

    return merged_data_with_status


def _merge_newer_data_no_checks_if_both_old_and_new(
    old_data: Union[pd.Series, pd.DataFrame], new_data: Union[pd.Series, pd.DataFrame]
) -> mergingDataWithStatus:

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

    return mergingDataWithStatus(
        status=MERGED_DATA,
        date_of_merge_join=first_date_in_new_data,
        merged_data=merged_data,
    )


def spike_check_merged_data(
    merged_data_with_status: mergingDataWithStatus,
    column_to_check_for_spike: str = arg_not_supplied,
    max_spike: float = VERY_BIG_NUMBER,
) -> mergingDataWithStatus:

    merge_status = merged_data_with_status.status
    merged_data = merged_data_with_status.merged_data

    if merge_status is OLD_DATA_ONLY:
        # No checking, just old data
        return merged_data_with_status

    if merge_status is NEW_DATA_ONLY:
        # check everything as there is no old data
        first_date_in_new_data = NO_MERGE_DATE
    else:
        first_date_in_new_data = merged_data_with_status.date_of_merge_join

    spike_date = _find_first_spike_in_data(
        merged_data,
        first_date_in_new_data,
        column_to_check_for_spike=column_to_check_for_spike,
        max_spike=max_spike,
    )

    merged_data_with_status.spike_date = spike_date

    return merged_data_with_status


def _find_first_spike_in_data(
    merged_data: Union[pd.Series, pd.DataFrame],
    date_of_merge_join: Union[datetime.datetime, object] = NO_MERGE_DATE,
    column_to_check_for_spike: str = arg_not_supplied,
    max_spike: float = VERY_BIG_NUMBER,
):
    """
    Checks to see if any data after last_date_in_old_data has spikes
    """
    data_to_check = _get_data_to_check(
        merged_data, column_to_check_for_spike=column_to_check_for_spike
    )
    change_in_vol_normalised_units = _calculate_change_in_vol_normalised_units(
        data_to_check
    )
    relevant_change_in_vol_normalised_units = (
        _get_relevant_period_in_vol_normalised_units_to_check(
            change_in_vol_normalised_units=change_in_vol_normalised_units,
            date_of_merge_join=date_of_merge_join,
        )
    )

    first_spike = _check_for_spikes_in_change_in_vol_normalised_units(
        relevant_change_in_vol_normalised_units=relevant_change_in_vol_normalised_units,
        max_spike=max_spike,
    )

    return first_spike


def _get_data_to_check(
    merged_data: Union[pd.Series, pd.DataFrame],
    column_to_check_for_spike: str = arg_not_supplied,
) -> Union[pd.Series, pd.DataFrame]:

    if is_a_series(merged_data):
        # already a series
        data_to_check = merged_data
    else:
        column_list = merged_data.columns
        if column_to_check_for_spike is arg_not_supplied:
            ## arbitrarily use first column
            column_to_check_for_spike = column_list[0]

        data_to_check = merged_data[column_to_check_for_spike]

    return data_to_check


def _calculate_change_in_vol_normalised_units(data_to_check: pd.Series) -> pd.Series:

    # Calculate the average change per day
    change_per_day = _calculate_change_in_daily_units(data_to_check)

    # absolute is what matters
    absolute_change_per_day = change_per_day.abs()

    # hard to know what span to use here as could be daily, intraday or a
    #     mixture...
    average_absolute_change = absolute_change_per_day.ewm(span=500).mean()

    change_in_vol_normalised_units = absolute_change_per_day / average_absolute_change

    return change_in_vol_normalised_units


def _calculate_change_in_daily_units(data_to_check: pd.Series) -> pd.Series:
    """
    Calculate the average change in daily units asssuming brownian motion
     for example, a change of 0.5 over half a day would be equal to a change of 0.5/sqrt(0.5) = 0.7 over a day
      a change of 2.0 over 5 days, would be equal to a change of 2/sqrt(5) = 0.89 a day
    >>> data_to_check1 = pd.Series([1,1,2], pd.date_range(datetime.datetime(2000,1,1), periods=3))
    >>> data_to_check2 = pd.Series([4,1,8], pd.date_range(datetime.datetime(2000,1,6), periods=3, freq="H"))
    >>> data_to_check = pd.concat([data_to_check1, data_to_check2], axis=0)
    >>> _calculate_change_in_daily_units(data_to_check)
    2000-01-02 00:00:00     0.000000
    2000-01-03 00:00:00     1.000000
    2000-01-06 00:00:00     1.154701
    2000-01-06 01:00:00   -14.696938
    2000-01-06 02:00:00    34.292856
    dtype: float64
    """
    data_diff = data_to_check.diff()[1:]
    index_diff = data_to_check.index[1:] - data_to_check.index[:-1]
    index_diff_days = [diff.total_seconds() / SECONDS_PER_DAY for diff in index_diff]

    change_in_daily_units_as_list = [
        diff / (diff_days**0.5)
        for diff, diff_days in zip(data_diff.values, index_diff_days)
    ]

    change_in_daily_units = pd.Series(
        change_in_daily_units_as_list, index=data_to_check.index[1:]
    )

    return change_in_daily_units


def _get_relevant_period_in_vol_normalised_units_to_check(
    change_in_vol_normalised_units: pd.Series,
    date_of_merge_join: Union[datetime.datetime, object] = NO_MERGE_DATE,
):
    if date_of_merge_join is NO_MERGE_DATE:
        # No merged data so we check it all
        relevant_change_in_vol_normalised_units = change_in_vol_normalised_units
    else:
        # just check more recent data
        relevant_change_in_vol_normalised_units = change_in_vol_normalised_units[
            date_of_merge_join:
        ]

    return relevant_change_in_vol_normalised_units


def _check_for_spikes_in_change_in_vol_normalised_units(
    relevant_change_in_vol_normalised_units: pd.Series,
    max_spike: float = VERY_BIG_NUMBER,
) -> Union[datetime.datetime, object]:

    if any(relevant_change_in_vol_normalised_units > max_spike):
        first_spike = relevant_change_in_vol_normalised_units.index[
            relevant_change_in_vol_normalised_units > max_spike
        ][0]
    else:
        first_spike = NO_SPIKE

    return first_spike


def full_merge_of_existing_data(
    old_data: Union[pd.Series, pd.DataFrame],
    new_data: Union[pd.Series, pd.DataFrame],
    keep_older: bool = True,
    check_for_spike: bool = False,
    max_spike: float = VERY_BIG_NUMBER,
    column_to_check_for_spike: str = arg_not_supplied,
):
    """
    Merges old data with new data.

    Any Nan in the existing data will ALWAYS be replaced (be careful!)

    If keep_older is False, then any value in the existing data which has the same index
        as in newer data will be replaced with newer data

    If you don't want to replace *any* existing data that occurs in time space before
       the earliest date of the new data, use merge_newer_data

    check_for_spike, max_spike, column_to_check are for spike checking
    """
    merged_data_with_status = full_merge_of_existing_data_no_checks(
        old_data, new_data, keep_older=keep_older
    )

    # check for spike
    if check_for_spike:
        merged_data_with_status = spike_check_merged_data(
            merged_data_with_status,
            column_to_check_for_spike=column_to_check_for_spike,
            max_spike=max_spike,
        )
        if merged_data_with_status.spike_present:
            return SPIKE_IN_DATA

    return merged_data_with_status.merged_data


def full_merge_of_existing_data_no_checks(
    old_data: Union[pd.Series, pd.DataFrame],
    new_data: Union[pd.Series, pd.DataFrame],
    keep_older: bool = True,
) -> mergingDataWithStatus:
    """
    Merges old data with new data.
    Any Nan in the existing data will be replaced (be careful!)

    Any Nan in the existing data will ALWAYS be replaced (be careful!)

    If keep_older is False, then any value in the existing data which has the same index
        as in newer data will be replaced with newer data
    """
    if len(old_data.index) == 0:
        return mergingDataWithStatus.only_new_data(new_data)
    if len(new_data.index) == 0:
        return mergingDataWithStatus.only_old_data(old_data)

    merged_data = full_merge_of_data_with_both_old_and_new(
        old_data=old_data, new_data=new_data, keep_older=keep_older
    )

    # get the difference between merged dataset and old one to get the earliest change
    actually_new_data = pd.concat([merged_data, old_data]).drop_duplicates(keep=False)

    if len(actually_new_data.index) == 0:
        return mergingDataWithStatus.only_old_data(old_data)

    first_date_in_new_data = actually_new_data.index[0]

    return mergingDataWithStatus(
        status=MERGED_DATA,
        date_of_merge_join=first_date_in_new_data,
        merged_data=merged_data,
    )


def full_merge_of_data_with_both_old_and_new(
    old_data: Union[pd.Series, pd.DataFrame],
    new_data: Union[pd.Series, pd.DataFrame],
    keep_older: bool = True,
) -> Union[pd.Series, pd.DataFrame]:

    if is_a_series(old_data):
        assert is_a_series(new_data)
        merged_data = full_merge_of_existing_series(
            old_series=old_data, new_series=new_data, keep_older=keep_older
        )
    else:
        assert is_a_dataframe(new_data)
        merged_data = full_merge_of_existing_dataframe(
            old_data=old_data, new_data=new_data, keep_older=keep_older
        )

    merged_data = merged_data.sort_index()

    return merged_data


def full_merge_of_existing_dataframe(
    old_data: Union[pd.Series, pd.DataFrame],
    new_data: pd.DataFrame,
    keep_older: bool = True,
) -> pd.DataFrame:
    """
    >>> old_data = pd.DataFrame(dict(a=[1,np.nan,3,np.nan], b=[np.nan,np.nan,7,np.nan]), index=pd.date_range(datetime.datetime(2000,1,1), periods=4))
    >>> new_data = pd.DataFrame(dict(a=[2,5, np.nan,8]), index=pd.date_range(datetime.datetime(2000,1,1), periods=4))
    >>> full_merge_of_existing_dataframe(old_data, new_data)
                  a    b
    2000-01-01  1.0  NaN
    2000-01-02  5.0  NaN
    2000-01-03  3.0  7.0
    2000-01-04  8.0  NaN
    >>> new_data = pd.DataFrame(dict(a=[2,5, np.nan,8], b=[1, np.nan, 8, 9]), index=pd.date_range(datetime.datetime(2000,1,1), periods=4))
    >>> full_merge_of_existing_dataframe(old_data, new_data, keep_older=False)
                  a    b
    2000-01-01  2.0  1.0
    2000-01-02  5.0  NaN
    2000-01-03  3.0  8.0
    2000-01-04  8.0  9.0
    """
    old_columns = old_data.columns

    merged_data_as_dict = {}
    for colname in old_columns:  ## Ignore new columns
        old_series = copy(old_data[colname])
        try:
            new_series = copy(new_data[colname])
        except KeyError:
            # missing from new data, so we just take the old
            merged_data_as_dict[colname] = old_series
            continue

        merged_series = full_merge_of_existing_series(
            old_series=old_series, new_series=new_series, keep_older=keep_older
        )
        merged_data_as_dict[colname] = merged_series

    merged_data = pd.DataFrame(merged_data_as_dict)

    return merged_data


def full_merge_of_existing_series(
    old_series: pd.Series, new_series: pd.Series, keep_older: bool = True
) -> pd.Series:
    """
    Merges old data with new data.
    Any Nan in the existing data will be replaced (be careful!)

    >>> old_series = pd.Series([1,np.nan,3,np.nan], pd.date_range(datetime.datetime(2000,1,1), periods=4))
    >>> new_series = pd.Series([2,5, np.nan,8], pd.date_range(datetime.datetime(2000,1,1), periods=4))
    >>> full_merge_of_existing_series(old_series, new_series)
    2000-01-01    1.0
    2000-01-02    5.0
    2000-01-03    3.0
    2000-01-04    8.0
    Freq: D, Name: original, dtype: float64
    >>> full_merge_of_existing_series(old_series, new_series, keep_older=False)
    2000-01-01    2.0
    2000-01-02    5.0
    2000-01-03    3.0
    2000-01-04    8.0
    """
    if len(old_series) == 0:
        return new_series
    if len(new_series) == 0:
        return old_series

    if keep_older:
        joint_data = pd.concat([old_series, new_series], axis=1)
        joint_data.columns = ["original", "new"]

        # fill to the left
        # NA from the original series will be preserved
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
    original_data, new_data, data_column="PRICE", label_column="PRICE_CONTRACT"
):
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

    :return: pd.DataFrame with two columns
    """

    if len(new_data) == 0:
        return original_data

    if len(original_data) == 0:
        return new_data

    # From the date after this, can happily merge new and old data
    match_data = find_dates_when_label_changes(
        original_data, new_data, data_column=data_column, label_column=label_column
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

    merged_data = full_merge_of_existing_series(
        original_data[data_column][
            original_data.index >= first_date_after_series_mismatch
        ],
        new_data[data_column][new_data.index >= first_date_after_series_mismatch],
    )

    labels_in_new_data = new_data[last_date_when_series_mismatch:][label_column]
    labels_in_old_data = original_data[:first_date_after_series_mismatch][label_column]
    labels_in_merged_data = pd.concat([labels_in_old_data, labels_in_new_data], axis=0)
    labels_in_merged_data = labels_in_merged_data.loc[
        ~labels_in_merged_data.index.duplicated(keep="first")
    ]
    labels_in_merged_data_reindexed = labels_in_merged_data.reindex(merged_data.index)

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
    original_data, new_data, data_column="PRICE", label_column="PRICE_CONTRACT"
):
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

    joint_labels = pd.concat(
        [original_data[label_column], new_data[label_column]], axis=1
    )
    joint_labels.columns = ["current", "new"]
    joint_labels = joint_labels.sort_index()

    new_data_start = new_data.index[0]

    existing_labels_in_new_period = joint_labels["current"][new_data_start:].ffill()
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
