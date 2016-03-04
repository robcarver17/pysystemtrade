'''
Trading rules for futures system
'''
from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.pdutils import divide_df_single_column
import pandas as pd


def ewmac(price, vol, Lfast, Lslow):
    """
    Calculate the ewmac trading fule forecast, given a price and EWMA speeds Lfast, Lslow and vol_lookback

    Assumes that 'price' is daily data

    This version recalculates the price volatility, and does not do capping or scaling

    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.DataFrame

    :param vol: The daily price unit volatility (NOT % vol)
    :type vol: pd.DataFrame (assumed Tx1)

    :param Lfast: Lookback for fast in days
    :type Lfast: int

    :param Lslow: Lookback for slow in days
    :type Lslow: int

    :returns: pd.DataFrame -- unscaled, uncapped forecast


    >>> from systems.provided.example.testdata import get_test_object_futures
    >>> from systems.basesystem import System
    >>> (rawdata, data, config)=get_test_object_futures()
    >>> system=System( [rawdata], data, config)
    >>>
    >>> ewmac(rawdata.get_instrument_price("EDOLLAR"), rawdata.daily_returns_volatility("EDOLLAR"), 64, 256).tail(2)
                   price
    2015-04-21  6.623348
    2015-04-22  6.468900
    """
    # price: This is the stitched price series
    # We can't use the price of the contract we're trading, or the volatility will be jumpy
    # And we'll miss out on the rolldown. See
    # http://qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html

    # We don't need to calculate the decay parameter, just use the span
    # directly

    fast_ewma = pd.ewma(price, span=Lfast)
    slow_ewma = pd.ewma(price, span=Lslow)
    raw_ewmac = fast_ewma - slow_ewma

    return divide_df_single_column(raw_ewmac, vol, ffill=(False, True))


def carry(daily_ann_roll, vol, smooth_days=90):
    """
    Calculate raw carry forecast, given annualised roll and volatility series (which must match)

    Assumes that everything is daily data

    :param daily_ann_roll: The annualised roll
    :type daily_ann_roll: pd.DataFrame (assumed Tx1)

    :param vol: The daily price unit volatility (NOT % vol)
    :type vol: pd.DataFrame (assumed Tx1)

    >>> from systems.provided.example.testdata import get_test_object_futures
    >>> from systems.basesystem import System
    >>> (rawdata, data, config)=get_test_object_futures()
    >>> system=System( [rawdata], data, config)
    >>>
    >>> carry(rawdata.daily_annualised_roll("EDOLLAR"), rawdata.daily_returns_volatility("EDOLLAR")).tail(2)
                annualised_roll_daily
    2015-04-21               0.350892
    2015-04-22               0.350892
    """

    ann_stdev = vol * ROOT_BDAYS_INYEAR
    raw_carry = divide_df_single_column(daily_ann_roll, ann_stdev, ffill=(False, True))
    smooth_carry = pd.ewma(raw_carry, smooth_days)

    return smooth_carry

if __name__ == '__main__':
    import doctest
    doctest.testmod()
