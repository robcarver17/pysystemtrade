"""
Algos.py

Basic building blocks of trading rules, like volatility measurement and
crossovers

"""
import math as maths
import numpy as np
import pandas as pd

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
    >>> calculate_weighted_average(np.array([0.2, 0.2, 0, 0.4]),np.array([2, np.nan, 3, np.nan]))
    0.4
    """
    weights_times_values_as_np = np_weights * np_values

    return np.nansum(weights_times_values_as_np)


def apply_with_min_periods(xcol, my_func=np.nanmean, min_periods=0):
    """
    :param x: data
    :type x: Tx1 pd.DataFrame

    :param func: Function to apply, if min periods met
    :type func: function

    :param min_periods: The minimum number of observations (*default* 10)
    :type min_periods: int

    :returns: pd.DataFrame Tx 1
    """
    not_nan = sum(~np.isnan(xcol))

    if not_nan >= min_periods:

        return my_func(xcol)
    else:
        return np.nan


def apply_buffer_single_period(
    last_position, optimal_position, top_pos, bot_pos, trade_to_edge
):
    """
    Apply a buffer to a position, single period

    If position is outside the buffer, we either trade to the edge of the
    buffer, or to the optimal

    :param last_position: last position we had
    :type last_position: float

    :param optimal_position: ideal position
    :type optimal_position: float

    :param top_pos: top of buffer
    :type top_pos: float

    :param bot_pos: bottom of buffer
    :type bot_pos: float

    :param trade_to_edge: Trade to the edge (TRue) or the optimal (False)
    :type trade_to_edge: bool

    :returns: float
    """

    if np.isnan(top_pos) or np.isnan(bot_pos) or np.isnan(optimal_position):
        return last_position

    if last_position > top_pos:
        if trade_to_edge:
            return top_pos
        else:
            return optimal_position
    elif last_position < bot_pos:
        if trade_to_edge:
            return bot_pos
        else:
            return optimal_position
    else:
        return last_position


def apply_buffer(
    optimal_position: pd.Series,
    pos_buffers: pd.DataFrame,
    trade_to_edge: bool = False,
    roundpositions: bool = False,
) -> pd.Series:
    """
    Apply a buffer to a position

    If position is outside the buffer, we either trade to the edge of the
    buffer, or to the optimal

    If we're rounding positions, then we floor and ceiling the buffers.

    :param position: optimal position
    :type position: pd.Series

    :param pos_buffers:
    :type pos_buffers: Tx2 pd.dataframe, top_pos and bot_pos

    :param trade_to_edge: Trade to the edge (TRue) or the optimal (False)
    :type trade_to_edge: bool

    :param round_positions: Produce rounded positions
    :type round_positions: bool

    :returns: pd.Series
    """

    pos_buffers = pos_buffers.ffill()
    use_optimal_position = optimal_position.ffill()

    top_pos = pos_buffers.top_pos
    bot_pos = pos_buffers.bot_pos

    if roundpositions:
        use_optimal_position = use_optimal_position.round()
        top_pos = top_pos.round()
        bot_pos = bot_pos.round()

    current_position = use_optimal_position.values[0]
    if np.isnan(current_position):
        current_position = 0.0

    buffered_position_list = [current_position]

    for idx in range(len(optimal_position.index))[1:]:
        current_position = apply_buffer_single_period(
            current_position,
            float(use_optimal_position.values[idx]),
            float(top_pos.values[idx]),
            float(bot_pos.values[idx]),
            trade_to_edge=trade_to_edge,
        )
        buffered_position_list.append(current_position)

    buffered_position = pd.Series(buffered_position_list, index=optimal_position.index)

    return buffered_position


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


def magnitude(x):
    return int(maths.log10(x))


def get_near_psd(A: np.array):
    C = (A + A.T) / 2
    eigval, eigvec = np.linalg.eig(C)
    eigval[eigval < 0] = 0

    return np.array(eigvec.dot(np.diag(eigval)).dot(eigvec.T))


if __name__ == "__main__":
    import doctest

    doctest.testmod()
