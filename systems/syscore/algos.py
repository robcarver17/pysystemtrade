"""
Algos

Basic building blocks of trading rules, like volatility measurement and crossovers

"""
import pandas as pd


def robust_vol_calc(x, days=35, volfloor=True, minquant=0.05, mincount=10, mincountformin=100, daysformin=500, absmin=0.0000000001):
    """
    Returns a N day rolling sigma
    
    Optionally: Uses 500 days to calculate sigma floor at 5% point
    
    Optionally (absmin is not None): remove very low values of vol
    """

    ## Standard deviation will be nan for first 10 non nan values
    vol=pd.ewmstd(x, span=days,min_periods=mincount)
    
    if absmin is not None:
        vol[vol<absmin]=absmin
    
    
    if volfloor:
        ## Find the rolling 5% quantile point to set as a minimum
        vol_min=pd.rolling_quantile(vol, daysformin, minquant, mincountformin)
        ## set this to zero for the first value then propogate forward, ensures we always have a value
        vol_min.set_value(vol_min.index[0],vol_min.columns[0],0.0)    
        vol_min=vol_min.ffill()

        ## apply the vol floor
        vol_with_min=pd.concat([vol, vol_min], axis=1)
        vol_floored=vol_with_min.max(axis=1, skipna=False).to_frame()
    else:
        vol_floored=vol
    
    return vol_floored

def calc_ewmac_forecast(price, Lfast, Lslow):
    """
    Calculate the ewmac trading fule forecast, given a price and EWMA speeds Lfast, Lslow and vol_lookback
    
    Assumes that 'price' is daily data
    """
    ## price: This is the stitched price series
    ## We can't use the price of the contract we're trading, or the volatility will be jumpy
    ## And we'll miss out on the rolldown. See http://qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html

    ## We don't need to calculate the decay parameter, just use the span directly
    
    fast_ewma=pd.ewma(price, span=Lfast)
    slow_ewma=pd.ewma(price, span=Lslow)
    raw_ewmac=fast_ewma - slow_ewma
    
    vol=robust_vol_calc(price.diff())    
    
    return raw_ewmac/vol

