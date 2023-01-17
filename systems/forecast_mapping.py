import numpy as np

from syscore.genutils import sign


def estimate_mapping_params(a_param):
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
