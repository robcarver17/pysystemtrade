'''
Simple trading rules used in examples
'''
import pandas as pd
from syscore.algos import robust_vol_calc
from syscore.pdutils import divide_df_single_column


def ewmac_forecast_with_defaults(price, Lfast=32, Lslow=128):
    """
    Calculate the ewmac trading fule forecast, given a price and EWMA speeds Lfast, Lslow and vol_lookback

    Assumes that 'price' is daily data

    This version recalculates the price volatility, and does not do capping or scaling

    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.DataFrame
    :param Lfast: Lookback for fast in days
    :type Lfast: int
    :param Lslow: Lookback for slow in days
    :type Lslow: int

    :returns: pd.DataFrame -- unscaled, uncapped forecast


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

    vol = robust_vol_calc(price.diff())

    return divide_df_single_column(raw_ewmac, vol)


def ewmac_forecast_with_defaults_no_vol(price, vol, Lfast=16, Lslow=32):
    """
    Calculate the ewmac trading fule forecast, given a price and EWMA speeds Lfast, Lslow and vol_lookback

    Assumes that 'price' is daily data

    This version recalculates the price volatility, and does not do capping or scaling

    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.DataFrame
    :param Lfast: Lookback for fast in days
    :type Lfast: int
    :param Lslow: Lookback for slow in days
    :type Lslow: int

    :returns: pd.DataFrame -- unscaled, uncapped forecast


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

    return divide_df_single_column(raw_ewmac, vol)
