'''
Correlations are important and used a lot
'''
from copy import copy

import numpy as np
import pandas as pd

from syscore.genutils import str2Bool, group_dict_from_natural, progressBar
from syscore.dateutils import generate_fitting_dates
from syscore.pdutils import df_from_list, must_have_item

from syslogdiag.log import logtoscreen


def get_avg_corr(sigma):
    """
    >>> sigma=np.array([[1.0,0.0,0.5], [0.0, 1.0, 0.75],[0.5, 0.75, 1.0]])
    >>> get_avg_corr(sigma)
    0.41666666666666669
    >>> sigma=np.array([[1.0,np.nan], [np.nan, 1.0]])
    >>> get_avg_corr(sigma)
    nan
    """
    new_sigma = copy(sigma)
    np.fill_diagonal(new_sigma, np.nan)
    if np.all(np.isnan(new_sigma)):
        return np.nan

    avg_corr = np.nanmean(new_sigma)

    return avg_corr


def clean_correlation(corrmat, corr_with_no_data, must_haves=None):
    """
    Make's sure we *always* have some kind of correlation matrix

    If corrmat is all nans, return corr_with_no_data

    Note nans must be replaced with 'some' value even if not used or things will go pair shaped

    :param corrmat: The correlation matrix to clea
    :type corrmat: 2-dim square np.array

    :param corr_with_no_data: The correlation matrix to use if this one all nans
    :type corr_with_no_data: 2-dim square np.array

    :param must_haves: The indices of things we must have weights for
    :type must_haves: list of bool

    :returns: 2-dim square np.array

    FIXME - this code is inefficient; especially if you use exponential weighting
             (since we'll be recalculating the same rolling correlations multiple times)

    >>> corr_with_no_data=boring_corr_matrix(3, offdiag=0.99, diag=1.0)
    >>> sigma=np.array([[1.0,0.0,0.5], [0.0, 1.0, 0.75],[0.5, 0.75, 1.0]])
    >>> clean_correlation(sigma, corr_with_no_data)
    array([[ 1.  ,  0.  ,  0.5 ],
           [ 0.  ,  1.  ,  0.75],
           [ 0.5 ,  0.75,  1.  ]])
    >>> sigma=np.array([[1.0,np.nan,0.5], [np.nan, 1.0, 0.75],[0.5, 0.75, 1.0]])
    >>> clean_correlation(sigma, corr_with_no_data)
    array([[ 1.   ,  0.625,  0.5  ],
           [ 0.625,  1.   ,  0.75 ],
           [ 0.5  ,  0.75 ,  1.   ]])
    >>> clean_correlation(sigma, corr_with_no_data, [True, True, True])
    array([[ 1.   ,  0.625,  0.5  ],
           [ 0.625,  1.   ,  0.75 ],
           [ 0.5  ,  0.75 ,  1.   ]])
    >>> clean_correlation(sigma, corr_with_no_data, [False, False, True])
    array([[ 1.  ,  0.99,  0.5 ],
           [ 0.99,  1.  ,  0.75],
           [ 0.5 ,  0.75,  1.  ]])
    >>> clean_correlation(sigma, corr_with_no_data, [False, True, True])
    array([[ 1.  ,  0.99,  0.5 ],
           [ 0.99,  1.  ,  0.75],
           [ 0.5 ,  0.75,  1.  ]])
    >>> sigma=np.array([[np.nan]*3]*3)
    >>> clean_correlation(sigma, corr_with_no_data)
    array([[ 1.  ,  0.99,  0.99],
           [ 0.99,  1.  ,  0.99],
           [ 0.99,  0.99,  1.  ]])
    """
    ###

    if must_haves is None:
        # assume all need to have data
        must_haves = [True] * corrmat.shape[0]

    if not np.any(np.isnan(corrmat)):
        # no cleaning required
        return corrmat

    if np.all(np.isnan(corrmat)):
        # all garbage
        return corr_with_no_data

    size_range = range(corrmat.shape[0])

    # We replace missing values that we must have with the average, or
    #   if not with the correlation value we use if there is no data at all

    avgcorr = get_avg_corr(corrmat)

    def _good_correlation(i, j, corrmat, avgcorr, must_haves,
                          corr_with_no_data):
        value = corrmat[i][j]
        must_have_value = must_haves[i] and must_haves[j]

        if np.isnan(value):
            if must_have_value:
                return avgcorr
            else:
                return corr_with_no_data[i][j]
        else:
            return value

    corrmat = np.array(
        [[
            _good_correlation(i, j, corrmat, avgcorr, must_haves,
                              corr_with_no_data) for i in size_range
        ] for j in size_range],
        ndmin=2)

    # makes life easier
    np.fill_diagonal(corrmat, 1.0)

    return corrmat


# FIXME: OLd fashioned way of doing correlation, kept so optimisation doesn't break
def correlation_single_period(data_for_estimate,
                              using_exponent=True,
                              min_periods=20,
                              ew_lookback=250,
                              floor_at_zero=False):
    """
    We generate a correlation from a pd.DataFrame, which could have been stacked up
    :param data_for_estimate: Data to get correlations from
    :type data_for_estimate: pd.DataFrame
    :param using_exponent: Should we use exponential weighting? If not every item is weighted equally
    :type using_exponent: bool
    :param ew_lookback: Lookback, in periods, for exp. weighting
    :type ew_lookback: int
    :param min_periods: Minimum periods before we get a correlation
    :type min_periods: int
    :returns: 2-dim square np.array
    FIX ME floor_at_zero IS NO LONGER USED KEPT TO STOP STUFF BREAKING
    """
    # These may come from config as str
    using_exponent = str2Bool(using_exponent)

    if using_exponent:
        # If we have stacked there will be duplicate dates
        # So we massage the span so it's correct
        # This assumes the index is at least daily and on same timestamp
        # This is an artifact of how we prepare the data
        # Usual use for IDM, FDM calculation when whole data set is used
        corrmat = data_for_estimate.ewm(
            span=ew_lookback, min_periods=min_periods).corr(pairwise=True)

        # only want the final one
        corrmat = corrmat.values[-1]
    else:
        # Use normal correlation
        # Usual use for bootstrapping when only have sub sample
        corrmat = data_for_estimate.corr(min_periods=min_periods)
        corrmat = corrmat.values

    return corrmat


class correlationSinglePeriod(object):
    def __init__(self,
                 data_as_df,
                 length_of_data=1,
                 ew_lookback=250,
                 boring_offdiag=0.99,
                 cleaning=True,
                 floor_at_zero=True,
                 **kwargs):
        """
        Create an object to calculate correlations

        We set up one of these with a set of data and parameters, and then call repeatedly

        :param data_as_df: The dataframe of correlations
        :param boring_offdiag: The off diagonal element to put into the matrix if data is absent
        :param cleaning: Should we include fake values in the matrix so we don't need a warm up period?
        :param floor_at_zero: Should we remove negative correlations?
        :param ew_lookback: Lookback to use if exponential calculation used
        :param length_of_data: Original length of data passed in (to correct for stacking of dataframe)

        :return: np.array of correlation matrix
        """

        self.cleaning = str2Bool(cleaning)
        self.floor_at_zero = str2Bool(floor_at_zero)

        ## correct the lookback if we're jamming stuff together
        self.ew_lookback_corrected = length_of_data * ew_lookback

        size = data_as_df.shape[1]
        self.corr_with_no_data = boring_corr_matrix(size, offdiag=np.nan)
        self.corr_for_cleaning = boring_corr_matrix(
            size, offdiag=boring_offdiag)

        self.kwargs = kwargs
        self.data_as_df = data_as_df

    def calculate(self, fit_period):
        """
        Work out the correlation for a single period

        :param fit_period: Specification of the period we're calculating the correlation for

        :return: np.array of correlation matrix
        """

        cleaning = self.cleaning

        corr_with_no_data = self.corr_with_no_data
        corr_for_cleaning = self.corr_for_cleaning

        data_as_df = self.data_as_df
        kwargs = self.kwargs
        ew_lookback_corrected = self.ew_lookback_corrected
        floor_at_zero = self.floor_at_zero

        if fit_period.no_data:
            # no data to fit with
            corrmat = corr_with_no_data
        else:

            data_for_estimate = data_as_df[fit_period.fit_start:
                                           fit_period.fit_end]

            corrmat = correlation_calculator(
                data_for_estimate, ew_lookback=ew_lookback_corrected, **kwargs)

        if cleaning:
            current_period_data = data_as_df[fit_period.fit_start:
                                             fit_period.fit_end]

            # must_haves are items with data in this period, so we need some kind of correlation
            must_haves = must_have_item(current_period_data)

            # means we can use earlier correlations with sensible values
            corrmat = clean_correlation(corrmat, corr_for_cleaning, must_haves)

            # can't do this earlier as might have nans
            if floor_at_zero:
                corrmat[corrmat < 0] = 0.0

        return corrmat


def correlation_calculator(data_for_estimate,
                           using_exponent=True,
                           min_periods=20,
                           ew_lookback=250):
    """
    We generate a correlation from a pd.DataFrame, which could have been stacked up

    :param data_for_estimate: Data to get correlations from
    :type data_for_estimate: pd.DataFrame

    :param using_exponent: Should we use exponential weighting? If not every item is weighted equally
    :type using_exponent: bool

    :param ew_lookback: Lookback, in periods, for exp. weighting
    :type ew_lookback: int

    :param min_periods: Minimum periods before we get a correlation
    :type min_periods: int

    :returns: 2-dim square np.array

    """
    # These may come from config as str

    using_exponent = str2Bool(using_exponent)

    if using_exponent:
        # If we have stacked there will be duplicate dates
        # So we massage the span so it's correct
        # This assumes the index is at least daily and on same timestamp
        # This is an artifact of how we prepare the data
        # Usual use for IDM, FDM calculation when whole data set is used
        corrmat = data_for_estimate.ewm(
            span=ew_lookback, min_periods=min_periods).corr(pairwise=True)

        # only want the final one
        corrmat = corrmat.values[-1]
    else:
        # Use normal correlation
        # Usual use for bootstrapping when only have sub sample
        corrmat = data_for_estimate.corr(min_periods=min_periods)
        corrmat = corrmat.values

    return corrmat


def boring_corr_matrix(size, offdiag=0.99, diag=1.0):
    """
    Create a boring correlation matrix

    :param size: dimensions
    :param offdiag: value to put in off diagonal
    :param diag: value to put in diagonal
    :return: np.array 2 dimensions, size
    """
    size_index = range(size)

    def _od(i, j, offdiag, diag):
        if i == j:
            return diag
        else:
            return offdiag

    m = [[_od(i, j, offdiag, diag) for i in size_index] for j in size_index]
    m = np.array(m)
    return m


class CorrelationList(object):
    '''
    A correlation list is a list of correlations, packed in with date information about them

    '''

    def __init__(self, corr_list, column_names, fit_dates):
        """
        Returns a time series of forecasts for a particular instrument

        :param instrument_code:
        :type str:

        :param rule_variation_list:
        :type list: list of str to get forecasts for, if None uses get_trading_rule_list

        :returns: TxN pd.DataFrames; columns rule_variation_name

        """

        setattr(self, "corr_list", corr_list)
        setattr(self, "columns", column_names)
        setattr(self, "fit_dates", fit_dates)

    def __repr__(self):
        return "%d correlation estimates for %s; use .corr_list, .columns, .fit_dates" % (
            len(self.corr_list), ",".join(self.columns))


class CorrelationEstimator(CorrelationList):
    '''

    We generate a correlation list from either a pd.DataFrame, or a list of them if we're pooling


    '''

    def __init__(self,
                 data,
                 frequency="W",
                 date_method="expanding",
                 rollyears=20,
                 **kwargs):
        """

        We generate a correlation from either a pd.DataFrame, or a list of them if we're pooling

        Its important that forward filling, or index / ffill / diff has been done before we begin

        :param data: Data to get correlations from
        :type data: pd.DataFrame or list if pooling

        :param frequency: Downsampling frequency. Must be "D", "W" or bigger
        :type frequency: str

        :param date_method: Method to pass to generate_fitting_dates
        :type date_method: str

        :param roll_years: If date_method is "rolling", number of years in window
        :type roll_years: int

        :param **kwargs: passed to correlationSinglePeriod

        :returns: CorrelationList
        """

        if type(data) is list:

            # turn the list of data into a single dataframe. This will have a unique time series, which we manage
            #   through adding a small offset of a few microseconds

            length_of_data = len(data)
            data_resampled = [
                data_item.resample(frequency).last() for data_item in data
            ]
            data_as_df = df_from_list(data_resampled)

        else:
            length_of_data = 1
            data_as_df = data.resample(frequency).last()

        column_names = list(data_as_df.columns)

        # Generate time periods
        fit_dates = generate_fitting_dates(
            data_as_df, date_method=date_method, rollyears=rollyears)

        # create a single period correlation estimator
        correlation_estimator_for_one_period = correlationSinglePeriod(
            data_as_df, length_of_data=length_of_data, **kwargs)

        # create a list of correlation matrices
        corr_list = []

        progress = progressBar(len(fit_dates), "Estimating correlations")
        # Now for each time period, estimate correlation
        for fit_period in fit_dates:

            progress.iterate()
            corrmat = correlation_estimator_for_one_period.calculate(
                fit_period)
            corr_list.append(corrmat)

        setattr(self, "corr_list", corr_list)
        setattr(self, "columns", column_names)
        setattr(self, "fit_dates", fit_dates)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
