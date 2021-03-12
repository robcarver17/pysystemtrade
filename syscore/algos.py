"""
Algos.py

Basic building blocks of trading rules, like volatility measurement and
crossovers

"""
import warnings

import numpy as np
import pandas as pd

from syscore.genutils import sign

LARGE_NUMBER_OF_DAYS = 250 * 100 * 100


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


def vol_estimator(x, using_exponent=True, min_periods=20, ew_lookback=250):
    """
    Generic vol estimator used for optimisation, works on data frames, produces
    a single answer

    :param x: data
    :type x: Tx1 pd.DataFrame

    :param using_exponent: Use exponential or normal vol (latter recommended
    for bootstrapping)
    :type using_exponent: bool

    :param min_periods: The minimum number of observations (*default* 10)
    :type min_periods: int

    :returns: pd.DataFrame -- volatility measure

    """
    if using_exponent:
        vol = (x.ewm(span=ew_lookback,
                     min_periods=min_periods).std().iloc[-1, :].values[0])

    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            vol = x.apply(
                apply_with_min_periods,
                axis=0,
                min_periods=min_periods,
                my_func=np.nanstd,
            )

    stdev_list = list(vol)

    return stdev_list


def mean_estimator(x, using_exponent=True, min_periods=20, ew_lookback=500):
    """
    Generic mean estimator used for optimisation, works on data frames

    :param using_exponent: Use exponential or normal vol (latter recommended
    for bootstrapping)
    :type using_exponent: bool

    """
    if using_exponent:
        means = (
            x.ewm(x, span=ew_lookback, min_periods=min_periods)
            .mean()
            .iloc[-1, :]
            .values[0]
        )

    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)

            means = x.apply(
                apply_with_min_periods,
                axis=0,
                min_periods=min_periods,
                my_func=np.nanmean,
            )

    mean_list = list(means)
    return mean_list


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
    optimal_position, pos_buffers, trade_to_edge=False, roundpositions=False
):
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
            trade_to_edge,
        )
        buffered_position_list.append(current_position)

    buffered_position = pd.Series(
        buffered_position_list,
        index=optimal_position.index)

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


def map_forecast_value(
        x,
        threshold=0.0,
        capped_value=20,
        a_param=1.0,
        b_param=1.0):
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
        map_forecast_value_scalar,
        args=(
            threshold,
            capped_value,
            a_param,
            b_param))


def robust_vol_calc(*args, **kwargs):
    raise Exception("robust_vol_calc has moved to sysquant.estimators.vol.robust_vol_calc - update your configuration!")


def forecast_scalar(*args, **kwargs):
    raise Exception("forecast_scalar has moved to sysquant.estimators.forecast_scalar.forecast_scalar - update your configuration!")


if __name__ == "__main__":
    import doctest

    doctest.testmod()
