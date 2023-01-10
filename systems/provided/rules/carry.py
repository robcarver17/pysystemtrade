def carry(raw_carry, smooth_days=90):
    """
    Calculate carry forecast, given that there exists a raw_carry() in rawdata

    Assumes that everything is daily data

    :param raw_carry: The annualised sharpe ratio of rolldown
    :type raw_carry: pd.DataFrame (assumed Tx1)

    >>> from systems.tests.testdata import get_test_object_futures
    >>> from systems.basesystem import System
    >>> (rawdata, data, config)=get_test_object_futures()
    >>> system=System( [rawdata], data, config)
    >>>
    >>> carry(rawdata.raw_carry("EDOLLAR")).tail(2)
    2015-12-10    0.411686
    2015-12-11    0.411686
    Freq: B, dtype: float64
    """

    smooth_carry = raw_carry.ewm(smooth_days).mean()

    return smooth_carry


def relative_carry(smoothed_carry_this_instrument, median_carry_for_asset_class):
    """
    Relative carry rule
    Suggested inputs: rawdata.smoothed_carry, rawdata.median_carry_for_asset_class

    :param smoothed_carry_this_instrument: pd.Series
    :param median_carry_for_asset_class: pd.Series aligned to smoothed_carry_this_instrument
    :return: forecast pd.Series
    """

    # should already be aligned
    relative_carry_forecast = (
        smoothed_carry_this_instrument - median_carry_for_asset_class
    )

    return relative_carry_forecast
