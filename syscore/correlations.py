'''
Correlations are important and used a lot
'''
from copy import copy


import numpy as np
import pandas as pd

from syscore.genutils import str2Bool, group_dict_from_natural
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
        must_haves = [True] * corrmat.shape[0]

    if not np.any(np.isnan(corrmat)):
        # no cleaning required
        return corrmat

    if np.all(np.isnan(corrmat)):
        return corr_with_no_data

    size_range = range(corrmat.shape[0])

    avgcorr = get_avg_corr(corrmat)

    def _good_correlation(i, j, corrmat, avgcorr,
                          must_haves, corr_with_no_data):
        value = corrmat[i][j]
        must_have_value = must_haves[i] and must_haves[j]

        if np.isnan(value):
            if must_have_value:
                return avgcorr
            else:
                return corr_with_no_data[i][j]
        else:
            return value

    corrmat = np.array([[_good_correlation(i, j, corrmat, avgcorr, must_haves, corr_with_no_data)
                         for i in size_range] for j in size_range], ndmin=2)

    # makes life easier and we'll deal with this later
    np.fill_diagonal(corrmat, 1.0)

    return corrmat


def correlation_single_period(data_for_estimate,
                              using_exponent=True, min_periods=20, ew_lookback=250,
                              floor_at_zero=True):
    """
    We generate a correlation from eithier a pd.DataFrame, or a list of them if we're pooling

    It's important that forward filling, or index / ffill / diff has been done before we begin

    also that we're on the right time frame, eg weekly if that's what we're doing

    :param data_for_estimate: Data to get correlations from
    :type data_for_estimate: pd.DataFrame

    :param using_exponent: Should we use exponential weighting?
    :type using_exponent: bool

    :param ew_lookback: Lookback, in periods, for exp. weighting
    :type ew_lookback: int

    :param min_periods: Minimum periods before we get a correlation
    :type min_periods: int

    :param floor_at_zero: remove negative correlations before proceeding
    :type floor_at_zero: bool or str

    :returns: 2-dim square np.array


    """
    # These may come from config as str
    using_exponent = str2Bool(using_exponent)

    if using_exponent:
        # If we stack there will be duplicate dates
        # So we massage the span so it's correct
        # This assumes the index is at least daily and on same timestamp
        # This is an artifact of how we prepare the data
        dindex = data_for_estimate.index
        dlenadj = float(len(dindex)) / len(set(list(dindex)))
        # Usual use for IDM, FDM calculation when whole data set is used
        corrmat = pd.ewmcorr(
            data_for_estimate,
            span=int(
                ew_lookback *
                dlenadj),
            min_periods=min_periods)

        # only want the final one
        corrmat = corrmat.values[-1]
    else:
        # Use normal correlation
        # Usual use for bootstrapping when only have sub sample
        corrmat = data_for_estimate.corr(min_periods=min_periods)
        corrmat = corrmat.values

    if floor_at_zero:
        corrmat[corrmat < 0] = 0.0

    return corrmat


def boring_corr_matrix(size, offdiag=0.99, diag=1.0):
    size_index = range(size)

    def _od(offdag, i, j):
        if i == j:
            return diag
        else:
            return offdiag
    m = [[_od(offdiag, i, j) for i in size_index] for j in size_index]
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
        return "%d correlation estimates for %s" % (
            len(self.corr_list), ",".join(self.columns))


class CorrelationEstimator(CorrelationList):
    '''

    We generate a correlation list from eithier a pd.DataFrame, or a list of them if we're pooling

    The default is to generate correlations annually, from weekly

    It's important that forward filling, or index / ffill / diff has been done before we begin


    '''

    def __init__(self, data, log=logtoscreen("optimiser"), frequency="W", date_method="expanding",
                 rollyears=20,
                 dict_group=dict(), boring_offdiag=0.99, cleaning=True, **kwargs):
        """

        We generate a correlation from eithier a pd.DataFrame, or a list of them if we're pooling

        Its important that forward filling, or index / ffill / diff has been done before we begin

        :param data: Data to get correlations from
        :type data: pd.DataFrame or list if pooling

        :param frequency: Downsampling frequency. Must be "D", "W" or bigger
        :type frequency: str

        :param date_method: Method to pass to generate_fitting_dates
        :type date_method: str

        :param roll_years: If date_method is "rolling", number of years in window
        :type roll_years: int

        :param dict_group: dictionary of groupings; used to replace missing values
        :type dict_group: dict

        :param boring_offdiag: Value used in creating 'boring' matrix, for when no data
        :type boring_offdiag: float

        :param **kwargs: passed to correlation_single_period

        :returns: CorrelationList
        """

        cleaning = str2Bool(cleaning)

        # grouping dictionary, convert to faster, algo friendly, form
        group_dict = group_dict_from_natural(dict_group)

        data = df_from_list(data)
        column_names = list(data.columns)

        data = data.resample(frequency, how="last")

        # Generate time periods
        fit_dates = generate_fitting_dates(
            data, date_method=date_method, rollyears=rollyears)

        size = len(column_names)
        corr_with_no_data = boring_corr_matrix(size, offdiag=boring_offdiag)

        # create a list of correlation matrices
        corr_list = []

        log.terse("Correlation estimate")

        # Now for each time period, estimate correlation
        for fit_period in fit_dates:
            log.msg("Estimating from %s to %s" %
                    (fit_period.period_start, fit_period.period_end))

            if fit_period.no_data:
                # no data to fit with
                corr_with_nan = boring_corr_matrix(
                    size, offdiag=np.nan, diag=np.nan)
                corrmat = corr_with_nan

            else:

                data_for_estimate = data[
                    fit_period.fit_start:fit_period.fit_end]

                corrmat = correlation_single_period(data_for_estimate,
                                                    **kwargs)

            if cleaning:
                current_period_data = data[
                    fit_period.fit_start:fit_period.fit_end]
                must_haves = must_have_item(current_period_data)

                # means we can use earlier correlations with sensible values
                corrmat = clean_correlation(
                    corrmat, corr_with_no_data, must_haves)

            corr_list.append(corrmat)

        setattr(self, "corr_list", corr_list)
        setattr(self, "columns", column_names)
        setattr(self, "fit_dates", fit_dates)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
