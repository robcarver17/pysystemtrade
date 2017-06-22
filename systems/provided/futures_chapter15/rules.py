'''
Trading rules for futures system
'''
from syscore.dateutils import ROOT_BDAYS_INYEAR
import pandas as pd


def ewmac(price, vol, Lfast, Lslow):
    """
    Calculate the ewmac trading fule forecast, given a price and EWMA speeds Lfast, Lslow and vol_lookback

    Assumes that 'price' and vol is daily data

    This version recalculates the price volatility, and does not do capping or scaling

    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.Series

    :param vol: The daily price unit volatility (NOT % vol)
    :type vol: pd.Series aligned to price

    :param Lfast: Lookback for fast in days
    :type Lfast: int

    :param Lslow: Lookback for slow in days
    :type Lslow: int

    :returns: pd.DataFrame -- unscaled, uncapped forecast


    >>> from systems.tests.testdata import get_test_object_futures
    >>> from systems.basesystem import System
    >>> (rawdata, data, config)=get_test_object_futures()
    >>> system=System( [rawdata], data, config)
    >>>
    >>> ewmac(rawdata.get_daily_prices("EDOLLAR"), rawdata.daily_returns_volatility("EDOLLAR"), 64, 256).tail(2)
    2015-12-10    5.327019
    2015-12-11    4.927339
    Freq: B, dtype: float64
    """
    # price: This is the stitched price series
    # We can't use the price of the contract we're trading, or the volatility will be jumpy
    # And we'll miss out on the rolldown. See
    # http://qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html

    # We don't need to calculate the decay parameter, just use the span
    # directly

    fast_ewma = price.ewm(span=Lfast).mean()
    slow_ewma = price.ewm(span=Lslow).mean()
    raw_ewmac = fast_ewma - slow_ewma

    return raw_ewmac / vol.ffill()


def carry(daily_ann_roll, vol, smooth_days=90):
    """
    Calculate raw carry forecast, given annualised roll and volatility series (which must match)

    Assumes that everything is daily data

    :param daily_ann_roll: The annualised roll
    :type daily_ann_roll: pd.DataFrame (assumed Tx1)

    :param vol: The daily price unit volatility (NOT % vol)
    :type vol: pd.DataFrame (assumed Tx1)

    >>> from systems.tests.testdata import get_test_object_futures
    >>> from systems.basesystem import System
    >>> (rawdata, data, config)=get_test_object_futures()
    >>> system=System( [rawdata], data, config)
    >>>
    >>> carry(rawdata.daily_annualised_roll("EDOLLAR"), rawdata.daily_returns_volatility("EDOLLAR")).tail(2)
    2015-12-10    0.411686
    2015-12-11    0.411686
    Freq: B, dtype: float64
    """
    print("DEPRECATED: USE carry2")
    ann_stdev = vol * ROOT_BDAYS_INYEAR
    raw_carry = daily_ann_roll / ann_stdev
    smooth_carry = raw_carry.ewm(smooth_days).mean()

    return smooth_carry


def carry2(raw_carry, smooth_days=90):
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
    >>> carry2(rawdata.raw_carry("EDOLLAR")).tail(2)
    2015-12-10    0.411686
    2015-12-11    0.411686
    Freq: B, dtype: float64
    """

    smooth_carry = raw_carry.ewm(smooth_days).mean()

    return smooth_carry


if __name__ == '__main__':
    import doctest
    doctest.testmod()
