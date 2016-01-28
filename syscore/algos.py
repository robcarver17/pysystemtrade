"""
Algos.py

Basic building blocks of trading rules, like volatility measurement and crossovers

"""
import pandas as pd
import numpy as np

from syscore.genutils import str2Bool
from systems.defaults import system_defaults

LARGE_NUMBER_OF_DAYS=250*100*100

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
    not_nan=sum([not np.isnan(xelement) for xelement in xcol])
    
    if not_nan>=min_periods:
    
        return my_func(xcol)
    else:
        return np.nan


def vol_estimator(x, using_exponent=True, min_periods=20, ew_lookback=250):
    """
    Generic vol estimator used for optimisation, works on data frames, produces a single answer

    :param x: data
    :type x: Tx1 pd.DataFrame

    :param using_exponent: Use exponential or normal vol (latter recommended for bootstrapping)
    :type using_exponent: bool

    :param min_periods: The minimum number of observations (*default* 10)
    :type min_periods: int


    :returns: pd.DataFrame -- volatility measure

    """
    if using_exponent:
        vol = pd.ewmstd(x, span=ew_lookback, min_periods=min_periods).iloc[-1,:].values[0]
        
    else:
        vol=x.apply(apply_with_min_periods,axis=0,min_periods=min_periods, my_func=np.nanstd) 
    
    stdev_list=list(vol)
    
    return stdev_list

def mean_estimator(x, using_exponent=True, min_periods=20, ew_lookback=500):
    """
    Generic mean estimator used for optimisation, works on data frames

    :param using_exponent: Use exponential or normal vol (latter recommended for bootstrapping)
    :type using_exponent: bool

    """
    if using_exponent:
        means=pd.ewma(x, span=ew_lookback, min_periods=min_periods).iloc[-1,:].values[0]
        
    else:
        means=x.apply(apply_with_min_periods,axis=0,min_periods=min_periods, my_func=np.nanmean)
            
    mean_list=list(means)
    
    return mean_list




def robust_vol_calc(x, days=35, min_periods=10, vol_abs_min=0.0000000001, vol_floor=True,
                    floor_min_quant=0.05, floor_min_periods=100,
                    floor_days=500):
    """
    Robust exponential volatility calculation, assuming daily series of prices
    We apply an absolute minimum level of vol (absmin);
    and a volfloor based on lowest vol over recent history

    :param x: data
    :type x: Tx1 pd.DataFrame

    :param days: Number of days in lookback (*default* 35)
    :type days: int

    :param min_periods: The minimum number of observations (*default* 10)
    :type min_periods: int

    :param vol_abs_min: The size of absolute minimum (*default* =0.0000000001) 0.0= not used
    :type absmin: float or None

    :param vol_floor Apply a floor to volatility (*default* True)
    :type vol_floor: bool
    :param floor_min_quant: The quantile to use for volatility floor (eg 0.05 means we use 5% vol) (*default 0.05)
    :type floor_min_quant: float
    :param floor_days: The lookback for calculating volatility floor, in days (*default* 500)
    :type floor_days: int
    :param floor_min_periods: Minimum observations for floor - until reached floor is zero (*default* 100)
    :type floor_min_periods: int

    :returns: pd.DataFrame -- volatility measure


    """

    # Standard deviation will be nan for first 10 non nan values
    vol = pd.ewmstd(x, span=days, min_periods=min_periods)

    vol[vol < vol_abs_min] = vol_abs_min

    if vol_floor:
        # Find the rolling 5% quantile point to set as a minimum
        vol_min = pd.rolling_quantile(
            vol, floor_days, floor_min_quant, floor_min_periods)
        # set this to zero for the first value then propogate forward, ensures
        # we always have a value
        vol_min.set_value(vol_min.index[0], vol_min.columns[0], 0.0)
        vol_min = vol_min.ffill()

        # apply the vol floor
        vol_with_min = pd.concat([vol, vol_min], axis=1)
        vol_floored = vol_with_min.max(axis=1, skipna=False).to_frame()
    else:
        vol_floored = vol

    vol_floored.columns = ["vol"]
    return vol_floored


def forecast_scalar(xcross, window=250000, min_periods=500, backfill=True):
    """
    Work out the scaling factor for xcross such that T*x has an abs value of 10
    
    :param x: 
    :type x: pd.DataFrame 1xT
    
    :param span:
    :type span: int
    
    :param min_periods:
    
    
    :returns: pd.DataFrame 
    """
    backfill=str2Bool(backfill) ## in yaml will come in as text
    ##We don't allow this to be changed in config
    target_abs_forecast = system_defaults['average_absolute_forecast']

    ## Take CS average first
    ## we do this before we get the final TS average otherwise get jumps in scalar
    if xcross.shape[1]==1:
        x=xcross.abs()
    else:
        x=xcross.abs().median(axis=1).to_frame()
    
    ## now the TS 
    avg_abs_value=pd.rolling_mean(x, window=window, min_periods=min_periods)
    scaling_factor=target_abs_forecast/avg_abs_value

    scaling_factor.columns=['scale_factor']
    
    if backfill:
        scaling_factor=scaling_factor.fillna(method="bfill")

    return scaling_factor




if __name__ == '__main__':
    import doctest
    doctest.testmod()
