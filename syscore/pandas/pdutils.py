"""
Utilities to help with pandas
"""
import pandas as pd
import datetime
import random

from collections import namedtuple
from copy import copy
from typing import Union, List
import numpy as np


from syscore.genutils import flatten_list
from syscore.dateutils import (
    BUSINESS_DAYS_IN_YEAR,
    check_time_matches_closing_time_to_second,
    CALENDAR_DAYS_IN_YEAR,
    SECONDS_IN_YEAR,
    NOTIONAL_CLOSING_TIME_AS_PD_OFFSET,
    WEEKS_IN_YEAR,
    MONTHS_IN_YEAR,
)
from syscore.objects import arg_not_supplied, missing_data, named_object

DEFAULT_DATE_FORMAT_FOR_CSV = "%Y-%m-%d %H:%M:%S"


def is_a_series(x: Union[pd.Series, pd.DataFrame]) -> bool:
    columns = getattr(x, "columns", None)
    return columns is None


def is_a_dataframe(x: Union[pd.Series, pd.DataFrame]) -> bool:
    return not is_a_series(x)


def interpolate_data_during_day(
    data_series: pd.Series, resample_freq="600S"
) -> pd.Series:
    set_of_data_by_day = [
        group[1] for group in data_series.groupby(data_series.index.date)
    ]
    interpolate_data_by_day = [
        interpolate_for_a_single_day(
            data_series_for_a_single_day, resample_freq=resample_freq
        )
        for data_series_for_a_single_day in set_of_data_by_day
    ]

    interpolated_data_as_single_series = pd.concat(interpolate_data_by_day, axis=0)

    return interpolated_data_as_single_series


def interpolate_for_a_single_day(
    data_series_for_single_day: pd.Series, resample_freq="600S"
) -> pd.Series:
    if len(data_series_for_single_day) < 2:
        return data_series_for_single_day

    resampled_data = data_series_for_single_day.resample(resample_freq).interpolate()

    return resampled_data


def top_and_tail(x: pd.DataFrame, rows=5) -> pd.DataFrame:
    return pd.concat([x[:rows], x[-rows:]], axis=0)


def resample_prices_to_business_day_index(x):
    return x.resample("1B").last()


def how_many_times_a_year_is_pd_frequency(frequency: str) -> float:
    DICT_OF_FREQ = {
        "B": BUSINESS_DAYS_IN_YEAR,
        "W": WEEKS_IN_YEAR,
        "M": MONTHS_IN_YEAR,
        "D": CALENDAR_DAYS_IN_YEAR,
    }

    times_a_year = DICT_OF_FREQ.get(frequency, missing_data)

    if times_a_year is missing_data:
        raise Exception(
            "Frequency %s is no good I only know about %s"
            % (frequency, str(list(DICT_OF_FREQ.keys())))
        )

    return float(times_a_year)


def sum_series(list_of_series: List[pd.Series], ffill=True) -> pd.Series:
    list_of_series_as_df = pd.concat(list_of_series, axis=1)
    if ffill:
        list_of_series_as_df = list_of_series_as_df.ffill()

    sum_of_series = list_of_series_as_df.sum(axis=1)

    return sum_of_series


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


def uniquets(x: Union[pd.Series, pd.DataFrame]) -> Union[pd.Series, pd.DataFrame]:
    """
    Makes x unique
    """
    x = x.groupby(level=0).last()
    return x


class listOfDataFrames(list):
    def ffill(self):
        ffill_data = [item.ffill() for item in self]
        return listOfDataFrames(ffill_data)

    def resample(self, frequency: str):
        data_resampled = [data_item.resample(frequency).last() for data_item in self]

        return listOfDataFrames(data_resampled)

    def resample_sum(self, frequency: str):
        data_resampled = [data_item.resample(frequency).sum() for data_item in self]

        return listOfDataFrames(data_resampled)

    def stacked_df_with_added_time_from_list(self) -> pd.DataFrame:
        data_as_df = stacked_df_with_added_time_from_list(self)

        return data_as_df

    def aligned(self):
        list_of_df_reindexed = self.reindex_to_common_index()
        list_of_df_common = list_of_df_reindexed.reindex_to_common_columns()

        return list_of_df_common

    def reindex_to_common_index(self):
        common_index = self.common_index()
        reindexed_data = self.reindex(common_index)

        return reindexed_data

    def reindex(self, new_index: list):
        data_reindexed = [data_item.reindex(new_index) for data_item in self]
        return listOfDataFrames(data_reindexed)

    def common_index(self):
        all_indices = [data_item.index for data_item in self]
        all_indices_flattened = flatten_list(all_indices)
        common_unique_index = list(set(all_indices_flattened))
        common_unique_index.sort()

        return common_unique_index

    def reindex_to_common_columns(self, padwith: float = 0.0):
        common_columns = self.common_columns()
        data_reindexed = [
            dataframe_pad(data_item, common_columns, pad_with_value=padwith)
            for data_item in self
        ]
        return listOfDataFrames(data_reindexed)

    def common_columns(self) -> list:
        all_columns = [data_item.columns for data_item in self]
        all_columns_flattened = flatten_list(all_columns)
        common_unique_columns = list(set(all_columns_flattened))
        common_unique_columns.sort()

        return common_unique_columns

    def fill_and_multipy(self) -> pd.DataFrame:
        list_of_df_common = self.aligned()
        list_of_df_common = list_of_df_common.ffill()
        result = list_of_df_common[0]
        for other in list_of_df_common[1:]:
            result = result * other

        return result


def stacked_df_with_added_time_from_list(data: listOfDataFrames) -> pd.DataFrame:
    """
    Create a single data frame from list of data frames

    Useful for fitting or calculating forecast correlations eg across instruments

    To preserve a unique time signature we add on 1..2..3... micro seconds to successive elements of the list

    WARNING: SO THIS METHOD WON'T WORK WITH HIGH FREQUENCY DATA!

    THIS WILL ALSO DESTROY ANY AUTOCORRELATION PROPERTIES

    >>> d1 = pd.DataFrame(dict(a=[1,2]), index=pd.date_range(datetime.datetime(2000,1,1),periods=2))
    >>> d2 = pd.DataFrame(dict(a=[5,6,7]), index=pd.date_range(datetime.datetime(2000,1,1),periods=3))
    >>> list_of_df = listOfDataFrames([d1, d2])
    >>> stacked_df_with_added_time_from_list(list_of_df)
                                a
    2000-01-01 00:00:00.000000  1
    2000-01-01 00:00:00.000001  5
    2000-01-02 00:00:00.000000  2
    2000-01-02 00:00:00.000001  6
    2000-01-03 00:00:00.000001  7
    """

    # ensure all are properly aligned
    # note we don't check that all the columns match here
    aligned_data = data.reindex_to_common_columns()

    # add on an offset
    for (offset_value, data_item) in enumerate(aligned_data):
        data_item.index = data_item.index + pd.Timedelta("%dus" % offset_value)

    # pooled
    # stack everything up
    stacked_data = pd.concat(aligned_data, axis=0)
    stacked_data = stacked_data.sort_index()

    return stacked_data


def get_column_names_in_df_with_at_least_one_value(df: pd.DataFrame) -> List[str]:
    """

    >>> df = pd.DataFrame(dict(a=[1,2], b=[np.nan, 3], c=[np.nan, np.nan]), index=pd.date_range(datetime.datetime(2000,1,1),periods=2))
    >>> get_column_names_in_df_with_at_least_one_value(df)
    ['a', 'b']
    """
    list_of_must_have = get_index_of_columns_in_df_with_at_least_one_value(df)
    columns = list(df.columns)
    must_have_columns = [
        col for idx, col in enumerate(columns) if list_of_must_have[idx]
    ]
    return must_have_columns


def get_index_of_columns_in_df_with_at_least_one_value(df: pd.DataFrame) -> List[bool]:
    """
    Returns the bool for columns of slice_data for which we have at least one non nan value

    >>> df = pd.DataFrame(dict(a=[1,2], b=[np.nan, 3], c=[np.nan, np.nan]), index=pd.date_range(datetime.datetime(2000,1,1),periods=2))
    >>> get_index_of_columns_in_df_with_at_least_one_value(df)
    [True, True, False]
    """

    return list(~df.isna().all().values)


def pd_readcsv(
    filename: str,
    date_index_name: str = "DATETIME",
    date_format: str = DEFAULT_DATE_FORMAT_FOR_CSV,
    input_column_mapping: Union[dict, named_object] = arg_not_supplied,
    skiprows: int = 0,
    skipfooter: int = 0,
) -> pd.DataFrame:
    """
    Reads a pandas data frame, with time index labelled
    package_name(/path1/path2.., filename

    :param filename: Filename with extension
    :param date_index_name: Column name of date index
    :param date_format: usual stfrtime format
    :param input_column_mapping: If supplied remaps column names in .csv file
    :param skiprows, skipfooter: passed to pd.read_csv

    :returns: pd.DataFrame

    """

    df = pd.read_csv(filename, skiprows=skiprows, skipfooter=skipfooter)

    ## Add time index as index
    df.index = pd.to_datetime(df[date_index_name], format=date_format).values
    del df[date_index_name]
    df.index.name = None

    if input_column_mapping is not arg_not_supplied:
        df = remap_columns_in_pd(df, input_column_mapping)

    return df


def remap_columns_in_pd(df: pd.DataFrame, input_column_mapping: dict) -> pd.DataFrame:
    """
    Returns the bool for columns of slice_data for which we have at least one non nan value

    >>> df = pd.DataFrame(dict(a=[1,2], b=[np.nan, 3]), index=pd.date_range(datetime.datetime(2000,1,1),periods=2))
    >>> remap_columns_in_pd(df, dict(b='a', a='b'))
                b    a
    2000-01-01  1  NaN
    2000-01-02  2  3.0
    """

    new_df = pd.DataFrame(index=df.index)
    for new_col_name, old_col_name in input_column_mapping.items():
        new_df[new_col_name] = df[old_col_name]

    return new_df


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


def reindex_last_monthly_include_first_date(df: pd.DataFrame) -> pd.DataFrame:
    df_monthly_index = list(df.resample("1M").last().index)  ## last day in month
    df_first_date_in_index = df.index[0]
    df_monthly_index = [df_first_date_in_index] + df_monthly_index
    df_reindex = df.reindex(df_monthly_index).ffill()

    return df_reindex


def weights_sum_to_one(weights: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure that weights for ecah row sum up to one, except where all weights are zero

    Preserves nans

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
    w
    """
    maxx = x.expanding(min_periods=1).max()
    return x - maxx


def from_dict_of_values_to_df(
    data_dict: dict, ts_index: pd.Index, columns: List[str] = arg_not_supplied
) -> pd.DataFrame:
    """
    Turn a set of fixed values into a pd.DataFrame that spans the long index

    >>> from_dict_of_values_to_df({'a':2, 'b':1}, ts_index = pd.date_range(datetime.datetime(2000,1,1),periods=4))
                a  b
    2000-01-01  2  1
    2000-01-02  2  1
    2000-01-03  2  1
    2000-01-04  2  1
    >>> from_dict_of_values_to_df({'a':2, 'b':1}, columns = ['b', 'a'],ts_index = pd.date_range(datetime.datetime(2000,1,1),periods=4))
                b  a
    2000-01-01  1  2
    2000-01-02  1  2
    2000-01-03  1  2
    2000-01-04  1  2

    """

    if columns is not arg_not_supplied:
        data_dict = {keyname: data_dict[keyname] for keyname in columns}

    pd_dataframe = pd.DataFrame(data_dict, ts_index)

    return pd_dataframe


def from_scalar_values_to_ts(scalar_value: float, ts_index: pd.Index) -> pd.Series:
    """
    Turn a scalar value into a pd.Series that spans the long index
    >>> from_scalar_values_to_ts(4, ts_index = pd.date_range(datetime.datetime(2000,1,1),periods=4))
    2000-01-01    4
    2000-01-02    4
    2000-01-03    4
    2000-01-04    4
    Freq: D, dtype: int64
    """

    pd_series = pd.Series(scalar_value, index=ts_index)

    return pd_series


def create_arbitrary_pdseries(
    data_list: list, date_start=datetime.datetime(1980, 1, 1), freq: str = "B"
) -> pd.Series:
    """
    Return a pandas Series with an arbitrary date index

    >>> create_arbitrary_pdseries([1,2,3])
    1980-01-01    1
    1980-01-02    2
    1980-01-03    3
    Freq: B, dtype: int64
    >>> create_arbitrary_pdseries([1,2,3], date_start = datetime.datetime(2000,1,1), freq="W")
    2000-01-02    1
    2000-01-09    2
    2000-01-16    3
    Freq: W-SUN, dtype: int64
    """

    date_index = pd.date_range(start=date_start, periods=len(data_list), freq=freq)
    pdseries = pd.Series(data_list, index=date_index)

    return pdseries


def dataframe_pad(
    starting_df: pd.DataFrame,
    target_column_list: List[str],
    pad_with_value: float = 0.0,
) -> pd.DataFrame:
    """
    Takes a dataframe and adds extra columns if necessary so we end up with columns named column_list

    >>> df = pd.DataFrame(dict(a=[1, 2, 3], b=[4 , 6, 5]), index=pd.date_range(datetime.datetime(2000,1,1),periods=3))
    >>> dataframe_pad(df, ['a','b','c'], pad_with_value=4.0)
                a  b    c
    2000-01-01  1  4  4.0
    2000-01-02  2  6  4.0
    2000-01-03  3  5  4.0
    >>> dataframe_pad(df, ['a','c'])
                a    c
    2000-01-01  1  0.0
    2000-01-02  2  0.0
    2000-01-03  3  0.0
    """

    def _pad_column(column_name: str, starting_df: pd.DataFrame, pad_with_value: float):
        if column_name in starting_df.columns:
            return starting_df[column_name]
        else:
            return pd.Series(
                np.full(starting_df.shape[0], pad_with_value), starting_df.index
            )

    new_data = [
        _pad_column(column_name, starting_df, pad_with_value)
        for column_name in target_column_list
    ]

    new_df = pd.concat(new_data, axis=1)
    new_df.columns = target_column_list

    return new_df


def apply_abs_min(x: pd.Series, min_value: float = 0.1) -> pd.Series:
    """
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


def make_df_from_list_of_named_tuple(
    tuple_class,
    list_of_tuples: list,
    make_index: bool = True,
    field_name_for_index: str = arg_not_supplied,
):
    """
    Turn a list of named tuplies into a dataframe
    The first element in the tuple will become the index

    >>> T = namedtuple('T', 'name value_a value_b')
    >>> t1 = T('X', 3,1)
    >>> t2 = T('Y',1,2)
    >>> t3 = T('Z', 4, 3)
    >>> make_df_from_list_of_named_tuple(T, [t1, t2, t3])
          value_a  value_b
    name
    X           3        1
    Y           1        2
    Z           4        3
    """
    elements = tuple_class._fields
    dict_of_elements = {}
    for element_name in elements:
        this_element_values = [
            getattr(list_entry, element_name) for list_entry in list_of_tuples
        ]
        dict_of_elements[element_name] = this_element_values

    pdf = pd.DataFrame(dict_of_elements)

    if make_index:
        if field_name_for_index is arg_not_supplied:
            field_name_for_index = elements[0]
        pdf.index = pdf[field_name_for_index]
        pdf = pdf.drop(labels=field_name_for_index, axis=1)

    return pdf


def set_pd_print_options():
    pd.set_option("display.max_rows", 500)
    pd.set_option("display.max_columns", 100)
    pd.set_option("display.width", 1000)


def closing_date_rows_in_pd_object(pd_object):
    return pd_object[
        [
            check_time_matches_closing_time_to_second(
                index_entry, NOTIONAL_CLOSING_TIME_AS_PD_OFFSET
            )
            for index_entry in pd_object.index
        ]
    ]


def intraday_date_rows_in_pd_object(pd_object):
    return pd_object[
        [
            not check_time_matches_closing_time_to_second(
                index_entry, NOTIONAL_CLOSING_TIME_AS_PD_OFFSET
            )
            for index_entry in pd_object.index
        ]
    ]


def get_intraday_df_at_frequency(df: pd.DataFrame, frequency="H"):
    intraday_only_df = intraday_date_rows_in_pd_object(df)
    intraday_df = intraday_only_df.resample(frequency).last()
    intraday_df_clean = intraday_df.dropna()

    return intraday_df_clean


def merge_data_with_different_freq(list_of_data: list):
    list_as_concat_pd = pd.concat(list_of_data, axis=0)
    sorted_pd = list_as_concat_pd.sort_index()
    unique_pd = uniquets(sorted_pd)

    return unique_pd


def sumup_business_days_over_pd_series_without_double_counting_of_closing_data(
    pd_series,
):
    intraday_data = intraday_date_rows_in_pd_object(pd_series)
    if len(intraday_data) == 0:
        return pd_series

    intraday_data_summed = intraday_data.resample("1B").sum()
    intraday_data_summed.name = "intraday"

    closing_data = closing_date_rows_in_pd_object(pd_series)
    closing_data_summed = closing_data.resample("1B").sum()

    both_sets_of_data = pd.concat([intraday_data_summed, closing_data_summed], axis=1)
    both_sets_of_data[both_sets_of_data == 0] = np.nan
    joint_data = both_sets_of_data.ffill(axis=1)
    joint_data = joint_data.iloc[:, 1]

    return joint_data


def replace_all_zeros_with_nan(result: pd.Series) -> pd.Series:
    check_result = copy(result)
    check_result[check_result == 0.0] = np.nan
    if all(check_result.isna()):
        result[:] = np.nan

    return result


def spread_out_annualised_return_over_periods(data_as_annual):
    period_intervals_in_seconds = (
        data_as_annual.index.to_series().diff().dt.total_seconds()
    )
    period_intervals_in_year_fractions = period_intervals_in_seconds / SECONDS_IN_YEAR
    data_per_period = data_as_annual * period_intervals_in_year_fractions

    return data_per_period


def from_series_to_matching_df_frame(
    pd_series: pd.Series, pd_df_to_match: pd.DataFrame, method="ffill"
) -> pd.DataFrame:
    list_of_columns = list(pd_df_to_match.columns)
    new_df = from_series_to_df_with_column_names(pd_series, list_of_columns)
    new_df = new_df.reindex(pd_df_to_match.index, method=method)

    return new_df


def from_series_to_df_with_column_names(
    pd_series: pd.Series, list_of_columns: list
) -> pd.DataFrame:

    new_df = pd.concat([pd_series] * len(list_of_columns), axis=1)
    new_df.columns = list_of_columns

    return new_df


if __name__ == "__main__":
    import doctest

    doctest.testmod()


def get_row_of_df_aligned_to_weights_as_dict(
    df: pd.DataFrame, relevant_date: datetime.datetime = arg_not_supplied
) -> dict:

    if relevant_date is arg_not_supplied:
        data_at_date = df.iloc[-1]
    else:
        try:
            data_at_date = df.loc[relevant_date]
        except KeyError:
            raise Exception("Date %s not found in data" % str(relevant_date))

    return data_at_date.to_dict()


def get_row_of_series(
    series: pd.Series, relevant_date: datetime.datetime = arg_not_supplied
):

    if relevant_date is arg_not_supplied:
        data_at_date = series.values[-1]
    else:
        try:
            data_at_date = series.loc[relevant_date]
        except KeyError:
            raise Exception("Date %s not found in data" % str(relevant_date))

    return data_at_date


def get_row_of_series_before_data(
    series: pd.Series, relevant_date: datetime.datetime = arg_not_supplied
):

    if relevant_date is arg_not_supplied:
        data_at_date = series.values[-1]
    else:
        index_point = get_max_index_before_datetime(series.index, relevant_date)
        data_at_date = series.values[index_point]

    return data_at_date


def get_max_index_before_datetime(index, date_point):
    matching_index_size = index[index < date_point].size

    if matching_index_size == 0:
        return None
    else:
        return matching_index_size - 1


def years_in_data(data: pd.Series) -> list:
    all_years = [x.year for x in data.index]
    unique_years = list(set(all_years))
    unique_years.sort()

    return unique_years


def calculate_cost_deflator(price: pd.Series) -> pd.Series:
    ## crude but doesn't matter
    daily_price = price.resample("1B").ffill()
    daily_returns = daily_price.ffill().diff()
    vol_price = daily_returns.rolling(180, min_periods=3).std().ffill()
    final_vol = vol_price[-1]

    cost_scalar = vol_price / final_vol

    return cost_scalar


def quantile_of_points_in_data_series(data_series):
    ## With thanks to https://github.com/PurpleHazeIan for this implementation
    numpy_series = np.array(data_series)
    results = []

    for irow in range(len(data_series)):
        current_value = numpy_series[irow]
        count_less_than = (numpy_series < current_value)[:irow].sum()
        results.append(count_less_than / (irow + 1))

    results_series = pd.Series(results, index=data_series.index)
    return results_series


def sort_df_ignoring_missing(df, column):
    # sorts df by column, with rows containing missing_data coming at the end
    missing = df[df[column] == missing_data]
    valid = df[df[column] != missing_data]
    valid_sorted = valid.sort_values(column)
    return pd.concat([valid_sorted, missing])


def apply_with_min_periods(xcol, my_func=np.nanmean, min_periods=0):
    """
    :param x: data
    :type x: Tx1 pd.DataFrame or series

    :param func: Function to apply, if min periods met
    :type func: function

    :param min_periods: The minimum number of observations
    :type min_periods: int

    :returns: output from function
    """
    not_nan = sum(~np.isnan(xcol))

    if not_nan >= min_periods:

        return my_func(xcol)
    else:
        return np.nan
