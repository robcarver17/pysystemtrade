from copy import copy
import pandas as pd
import numpy as np
from dataclasses import dataclass
from syscore.objects import arg_not_supplied
from syscore.pdutils import must_have_item

from sysquant.fitting_dates import fitDates


class Correlation(object):
    def __init__(self, values: np.array, columns =arg_not_supplied):
        if columns is arg_not_supplied:
            columns = [""]*len(values)
        self._values = values
        self._columns = columns

    def __repr__(self):
        return str(self.as_pd())

    def as_pd(self):
        values = self.values
        columns = self.columns

        return pd.DataFrame(values, index = columns, columns=columns)


    @property
    def values(self) -> np.array:
        return self._values

    @property
    def columns(self) -> list:
        return self._columns

    @property
    def size(self) -> int:
        return len(self.columns)

    def all_values_present(self):
        return not np.any(np.isnan(self.values))

    def no_values_present(self):
        return np.all(np.isnan(self.values))

    def clean_corr_matrix_given_data(self,
                                     fit_period: fitDates,
                                     data_for_correlation: pd.DataFrame):
        if fit_period.no_data:
            return self

        current_period_data = data_for_correlation[fit_period.fit_start: fit_period.fit_end]

        # must_haves are items with data in this period, so we need some
        # kind of correlation
        must_haves = must_have_item(current_period_data)

        clean_correlation = self.clean_correlations(must_haves)

        return clean_correlation

    def clean_correlations(self, must_haves: list =arg_not_supplied, offdiag = 0.99):

        # means we can use earlier correlations with sensible values
        cleaned_corr_matrix = clean_correlation(self, must_haves, offdiag=offdiag)

        return cleaned_corr_matrix

    def boring_corr_matrix(self,
                           offdiag: float=0.99,
                       diag: float=1.0):

        return create_boring_corr_matrix(self.size, offdiag=offdiag, diag = diag)

    def floor_correlation_matrix(self,  floor=0.0):
        corr_matrix_values = copy(self.values)
        corr_matrix_values[corr_matrix_values < floor] = floor
        corr_matrix = Correlation(corr_matrix_values, self.columns)
        return corr_matrix

    def average_corr(self) -> float:
        new_corr_values = copy(self.values)
        np.fill_diagonal(new_corr_values, np.nan)
        if np.all(np.isnan(new_corr_values)):
            return np.nan

        avg_corr = np.nanmean(new_corr_values)

        return avg_corr



def create_boring_corr_matrix(size: int,
                       offdiag: float=0.99,
                       diag: float=1.0,
                              columns = arg_not_supplied) -> Correlation:
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

    corr_matrix_values_as_list = [[_od(i, j, offdiag, diag) for i in size_index] for j in size_index]
    corr_matrix_values = np.array(corr_matrix_values_as_list)

    boring_corr_matrix = Correlation(corr_matrix_values, columns)

    return boring_corr_matrix


def clean_correlation(raw_corr_matrix: Correlation,
                      must_haves=arg_not_supplied,
                      offdiag = 0.99) -> Correlation:
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


    >>> sigma=np.array([[1.0,0.0,0.5], [0.0, 1.0, 0.75],[0.5, 0.75, 1.0]])
    >>> cmatrix = Correlation(sigma)
    >>> clean_correlation(sigma).values
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

    if must_haves is arg_not_supplied:
        # assume all need to have data
        must_haves = [True] * raw_corr_matrix.size

    assert len(must_haves) == raw_corr_matrix.size

    if raw_corr_matrix.all_values_present():
        # no cleaning required
        return raw_corr_matrix

    corr_for_cleaning = raw_corr_matrix.boring_corr_matrix(offdiag=offdiag)

    if raw_corr_matrix.no_values_present():
        # all garbage
        return corr_for_cleaning

    corrmat_values = _get_cleaned_matrix_values(raw_corr_matrix,
                                                must_haves=must_haves,
                                                corr_for_cleaning=corr_for_cleaning)

    cleaned_corr_matrix = Correlation(corrmat_values, raw_corr_matrix.columns)

    return cleaned_corr_matrix

def _get_cleaned_matrix_values(raw_corr_matrix: Correlation,
                               must_haves: list,
                               corr_for_cleaning: Correlation) -> np.array:
    size_range = range(raw_corr_matrix.size)

    # We replace missing values that we must have with the average, or
    #   if not with the correlation value we use if there is no data at all

    avgcorr = raw_corr_matrix.average_corr()

    def _good_correlation(
            i,
            j,
            corrmat_as_array,
            avgcorr,
            must_haves,
            corr_with_no_data_as_array):
        if i==j:
            return 1.0
        value = corrmat_as_array[i][j]
        must_have_value = must_haves[i] and must_haves[j]

        if np.isnan(value):
            if must_have_value:
                return avgcorr
            else:
                return corr_with_no_data_as_array[i][j]
        else:
            return value

    corrmat_as_array = raw_corr_matrix.values
    corr_with_no_data_as_array = corr_for_cleaning.values
    corrmat_values = np.array(
        [
            [
                _good_correlation(i, j, corrmat_as_array, avgcorr, must_haves, corr_with_no_data_as_array)
                for i in size_range
            ]
            for j in size_range
        ],
        ndmin=2,
    )

    return corrmat_values

@dataclass
class CorrelationList:
    corr_list: list
    column_names: list
    fit_dates: list

    def __repr__(self):
        return (
            "%d correlation estimates for %s; use .corr_list, .columns, .fit_dates" %
            (len(
                self.corr_list), ",".join(
                self.column_names)))