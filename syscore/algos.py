"""
Algos.py

Basic building blocks of trading rules, like volatility measurement and
crossovers

"""
import math as maths
import numpy as np

from syscore.genutils import sign
from copy import copy


def calculate_weighted_average_with_nans(
    weights: list, list_of_values: list, sum_of_weights_should_be: float = 1.0
) -> float:

    """
    Calculate a weighted average when the weights and/or values might be nans
    >>> calculate_weighted_average_with_nans([0.2, 0.2, np.nan, 0.4],[2, np.nan, 3, np.nan])
    2.0
    >>> calculate_weighted_average_with_nans([np.nan, 0.2, np.nan, 0.4],[2, np.nan, 3, np.nan])
    0.0

    """
    ## easier to work in np space
    np_weights = np.array(weights)
    np_values = np.array(list_of_values)

    # get safe weights
    np_weights_without_nans_in_weights_or_values = (
        calculate_np_weights_without_nans_in_weights_or_values(
            np_weights=np_weights, np_values=np_values
        )
    )

    normalised_weights = renormalise_array_of_values_to_sum(
        np_weights_without_nans_in_weights_or_values,
        renormalise_sum_to=sum_of_weights_should_be,
    )

    weighted_value = calculate_weighted_average(
        np_weights=normalised_weights, np_values=np_values
    )

    return weighted_value


def calculate_np_weights_without_nans_in_weights_or_values(
    np_weights: np.array, np_values: np.array
) -> np.array:
    """
    Get set of weights where neithier the value or the weight is nan
    >>> calculate_np_weights_without_nans_in_weights_or_values(np.array([0.2, 0.2, np.nan, 0.4]),np.array([2, np.nan, 3, np.nan]))
    array([0.2, 0. , 0. , 0. ])
    """

    weights_times_values_as_np = np_weights * np_values
    empty_weights = np.isnan(weights_times_values_as_np)

    weights_without_nan = copy(np_weights)
    weights_without_nan[empty_weights] = 0.0

    return weights_without_nan


def renormalise_array_of_values_to_sum(
    array_of_values: np.array, renormalise_sum_to: float = 1.0
) -> np.array:
    """
    Most commonly used to renormalise weights to 1.0

    >>> renormalise_array_of_values_to_sum(np.array([0.125, 0.125, 0.25, 0.0]), 2.0)
    array([0.5, 0.5, 1. , 0. ])

    """
    sum_of_values = np.nansum(array_of_values)
    renormalise_multiplier = renormalise_sum_to / sum_of_values
    new_values = array_of_values * renormalise_multiplier

    return new_values


def calculate_weighted_average(np_weights: np.array, np_values: np.array) -> float:
    """
    Implicit replaces nan with zeros

    >>> calculate_weighted_average(np.array([0.2, 0.2, 0, 0.4]),np.array([2, np.nan, 3, np.nan]))
    0.4
    """
    weights_times_values_as_np = np_weights * np_values

    return np.nansum(weights_times_values_as_np)


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


def return_mapping_params(a_param):
    """
    The process of non-linear mapping is designed to ensure that we can still trade with small account sizes

    We want to end up with a function like this, for raw forecast x and mapped forecast m,
        capped_value c and threshold_value t:

    if -t < x < +t: m=0
    if abs(x)>c: m=sign(x)*c*a
    if c < x < -t:   (x+t)*b
    if t < x < +c:   (x-t)*b

    Where a,b are set such that the std(x) = std(m), assuming a gaussian distribution
    and so that (c-t)*b = c * a; i.e. b = (c*a)/(c-t)

    We set a such that at the capped value we have sufficient contracts

    :return: tuple
    """

    capped_value = 20  # fitted function doesn't work otherwise
    assert a_param > 1.2  # fitted function doesn't work otherwise
    assert a_param <= 1.7

    threshold_value = -19.811 + 22.263 * a_param
    assert threshold_value < capped_value

    b_param = (capped_value * a_param) / (capped_value - threshold_value)

    return (a_param, b_param, threshold_value, capped_value)


def map_forecast_value_scalar(x, threshold, capped_value, a_param, b_param):
    """
    Non linear mapping of x value; replaces forecast capping; with defaults will map 1 for 1

    We want to end up with a function like this, for raw forecast x and mapped forecast m,
        capped_value c and threshold_value t:

    if -t < x < +t: m=0
    if abs(x)>c: m=sign(x)*c*a
    if c < x < -t:   (x+t)*b
    if t < x < +c:   (x-t)*b

    :param x: value to map
    :param threshold: value below which map to zero
    :param capped_value: maximum value we want x to take (without non linear mapping)
    :param a_param: slope
    :param b_param:
    :return: mapped x
    """
    x = float(x)
    if np.isnan(x):
        return x
    if abs(x) < threshold:
        return 0.0
    if x >= -capped_value and x <= -threshold:
        return b_param * (x + threshold)
    if x >= threshold and x <= capped_value:
        return b_param * (x - threshold)
    if abs(x) > capped_value:
        return sign(x) * capped_value * a_param

    raise Exception("This should cover all conditions!")


def map_forecast_value(x, threshold=0.0, capped_value=20, a_param=1.0, b_param=1.0):
    """
    Non linear mapping of x value; replaces forecast capping; with defaults will map 1 for 1, across time series

    We want to end up with a function like this, for raw forecast x and mapped forecast m,
        capped_value c and threshold_value t:

    if -t < x < +t: m=0
    if abs(x)>c: m=sign(x)*c*a
    if c < x < -t:   (x+t)*b
    if t < x < +c:   (x-t)*b

    :param x: value to map
    :param threshold: value below which map to zero
    :param capped_value: maximum value we want x to take (without non linear mapping)
    :param a_param: slope
    :param b_param:
    :return: mapped x
    """

    return x.apply(
        map_forecast_value_scalar, args=(threshold, capped_value, a_param, b_param)
    )


def calculate_multiplication_factor_for_nice_repr_of_value(some_value: float) -> float:
    """
    Work out a multiplication factor to avoid having to print a mantissa repr
    >>> calculate_multiplication_factor_for_nice_repr_of_value(3.2)
    1.0
    >>> calculate_multiplication_factor_for_nice_repr_of_value(0.032)
    1.0
    >>> calculate_multiplication_factor_for_nice_repr_of_value(0.0032)
    100.0
    >>> calculate_multiplication_factor_for_nice_repr_of_value(0.00032)
    1000.0
    >>> calculate_multiplication_factor_for_nice_repr_of_value(0.000000000000000001)
    1e+18
    """
    BIG_ENOUGH = 0.01
    ARBITRARY_LARGE_MULTIPLIER = 1000000
    NO_MULTIPLIER_REQUIRED = 1.0

    if some_value > BIG_ENOUGH:
        return NO_MULTIPLIER_REQUIRED

    if some_value == 0:
        return ARBITRARY_LARGE_MULTIPLIER

    mag = magnitude(some_value)
    mult_factor = 10.0 ** (-mag)

    return mult_factor


def magnitude(x):
    """
    Magnitude of a positive numeber. Used for calculating significant figures
    """
    return int(maths.log10(x))


if __name__ == "__main__":
    import doctest

    doctest.testmod()
