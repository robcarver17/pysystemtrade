"""
Utilities to help with pandas
"""
import pandas as pd
import datetime
import random

import numpy as np
from copy import copy

from syscore.genutils import flatten_list
from syscore.dateutils import (
    BUSINESS_DAYS_IN_YEAR,
    time_matches,
    CALENDAR_DAYS_IN_YEAR,
SECONDS_IN_YEAR,
    NOTIONAL_CLOSING_TIME_AS_PD_OFFSET,
WEEKS_IN_YEAR,
MONTHS_IN_YEAR

)
from syscore.objects import arg_not_supplied

DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def how_many_times_a_year_is_pd_frequency(frequency: str) -> float:
    DICT_OF_FREQ = {'B': BUSINESS_DAYS_IN_YEAR,
                    'W': WEEKS_IN_YEAR,
                    'M': MONTHS_IN_YEAR,
                    'D': CALENDAR_DAYS_IN_YEAR}

    times_a_year = DICT_OF_FREQ.get(frequency, None)

    if times_a_year is None:
        raise Exception("Frequency %s is no good I only know about %s" %
                        (frequency, str(list(DICT_OF_FREQ.keys()))))

    return float(times_a_year)

def sum_series(list_of_series: list, ffill = True)-> pd.Series:
    list_of_series_as_df = pd.concat(list_of_series, axis=1)
    if ffill:
        list_of_series_as_df = list_of_series_as_df.ffill()

    sum_of_series = list_of_series_as_df.sum(axis=1)

    return sum_of_series


def turnover(x, y):
    """
    Gives the turnover of x, once normalised for y

    Returned in annualised terms

    """

    daily_x = x.resample("1B").last()
    if isinstance(y, float) or isinstance(y, int):
        daily_y = pd.Series(np.full(daily_x.shape[0], float(y)), daily_x.index)
    else:
        daily_y = y.resample("1B").last()

    norm_x = daily_x / daily_y.ffill()

    avg_daily = float(norm_x.diff().abs().mean())

    return avg_daily * BUSINESS_DAYS_IN_YEAR



def uniquets(x):
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
        data_resampled = [
            data_item.resample(frequency).last() for data_item in self
        ]

        return listOfDataFrames(data_resampled)

    def resample_sum(self, frequency: str):
        data_resampled = [
            data_item.resample(frequency).sum() for data_item in self
        ]

        return listOfDataFrames(data_resampled)

    def stacked_df_with_added_time_from_list(self) -> pd.DataFrame:
        data_as_df = stacked_df_with_added_time_from_list(self)

        return data_as_df

    def reindex_to_common_index(self):
        common_index = self.common_index()
        reindexed_data = self.reindex(common_index)

        return reindexed_data

    def reindex(self, new_index: list):
        data_reindexed = [
            data_item.reindex(new_index)
            for data_item in self
        ]
        return listOfDataFrames(data_reindexed)

    def common_index(self):
        all_indices = [data_item.index for data_item in self]
        all_indices_flattened = flatten_list(all_indices)
        common_unique_index = list(set(all_indices_flattened))
        common_unique_index.sort()

        return common_unique_index

    def common_columns(self):
        all_columns = [data_item.columns for data_item in self]
        all_columns_flattened = flatten_list(all_columns)
        common_unique_columns = list(set(all_columns_flattened))
        common_unique_columns.sort()

        return listOfDataFrames(common_unique_columns)

    def reindex_to_common_columns(self, padwith=0.0):
        common_columns = self.common_columns()
        data_reindexed = [
            dataframe_pad(data_item, common_columns, padwith=padwith)
            for data_item in self
        ]
        return listOfDataFrames(data_reindexed)

    def aligned(self):
        list_of_df_reindexed = self.reindex_to_common_index()
        list_of_df_common = list_of_df_reindexed.reindex_to_common_columns()

        return list_of_df_common

    def fill_and_multipy(self):
        list_of_df_common = self.aligned()
        list_of_df_common = list_of_df_common.ffill()
        result = list_of_df_common[0]
        for other in list_of_df_common[1:]:
            result = result * other

        return result



def stacked_df_with_added_time_from_list(data: listOfDataFrames) -> pd.DataFrame:
    """
    Create a single data frame from list of data frames

    To preserve a unique time signature we add on 1..2..3... micro seconds to successive elements of the list

    WARNING: SO THIS METHOD WON'T WORK WITH HIGH FREQUENCY DATA!

    THIS WILL ALSO DESTROY ANY AUTOCORRELATION PROPERTIES
    """


    if isinstance(data, list) or isinstance(data, listOfDataFrames):
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

    return list(~slice_data.isna().all().values)

def get_bootstrap_series(data: pd.DataFrame):
    length_of_series = len(data.index)
    random_indices = [int(random.uniform(0,length_of_series)) for _unused in range(length_of_series)]
    bootstrap_data = data.iloc[random_indices]

    return bootstrap_data


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
    normalised_weights = weights_sum_to_one(adj_weights)

    return normalised_weights

def weights_sum_to_one(weights: pd.DataFrame):
    sum_weights = weights.sum(axis=1)
    sum_weights[sum_weights==0.0] = 0.0001
    weight_multiplier = 1.0 / sum_weights
    weight_multiplier_array = np.array([weight_multiplier]*len(weights.columns))
    weight_values = weights.values

    normalised_weights_np = weight_multiplier_array.transpose() * weight_values
    normalised_weights = pd.DataFrame(normalised_weights_np,
                                      columns = weights.columns,
                                      index = weights.index)

    return normalised_weights


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

    ts_index = [long_ts_index[0], long_ts_index[-1]]

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

    pd_series = pd.Series([scalar_value]*len(long_ts_index), index = long_ts_index)

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
            return pd.Series(np.full(starting_df.shape[0], 0.0), starting_df.index)

    new_data = [_pad_column(column_name, starting_df, padwith)
                for column_name in column_list]

    new_df = pd.concat(new_data, axis=1)
    new_df.columns = column_list

    return new_df

def apply_abs_min(x: pd.Series, min_value=0.1):
    x[(x<min_value) & (x>0)] = min_value
    x[(x > min_value) & (x < 0)] = -min_value

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


def spread_out_annualised_return_over_periods(data_as_annual):
    period_intervals_in_seconds = data_as_annual.index.to_series().diff().dt.total_seconds()
    period_intervals_in_year_fractions = period_intervals_in_seconds / SECONDS_IN_YEAR
    data_per_period = data_as_annual * period_intervals_in_year_fractions

    return data_per_period

def from_series_to_matching_df_frame(pd_series: pd.Series,
                                     pd_df_to_match: pd.DataFrame,
                                     method="ffill") -> pd.DataFrame:
    list_of_columns = list(pd_df_to_match.columns)
    new_df = from_series_to_df_with_column_names(pd_series, list_of_columns)
    new_df = new_df.reindex(pd_df_to_match.index, method=method)

    return new_df

def from_series_to_df_with_column_names(pd_series: pd.Series,
                                        list_of_columns: list) -> pd.DataFrame:

    new_df = pd.concat([pd_series]*len(list_of_columns), axis=1)
    new_df.columns = list_of_columns

    return new_df

if __name__ == "__main__":
    import doctest

    doctest.testmod()


def get_row_of_df_aligned_to_weights_as_dict(df: pd.DataFrame,
                                             relevant_date: datetime.datetime = arg_not_supplied) \
    -> dict:

    if relevant_date is arg_not_supplied:
        data_at_date = df.iloc[-1]
    else:
        try:
            data_at_date = df.loc[relevant_date]
        except KeyError:
            raise Exception("Date %s not found in portfolio weights" % str(relevant_date))

    return data_at_date.to_dict()