from copy import copy
from typing import Union

import pandas as pd

from syscore.pandas.merge_data_keeping_past_data import (
    VERY_BIG_NUMBER,
    spike_check_merged_data,
    SPIKE_IN_DATA,
    mergingDataWithStatus,
    MERGED_DATA,
)
from syscore.constants import arg_not_supplied
from syscore.pandas.pdutils import is_a_series, is_a_dataframe


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
    >>> import numpy as np, datetime
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

    >>> import numpy as np, datetime
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
    Freq: D, dtype: float64
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
