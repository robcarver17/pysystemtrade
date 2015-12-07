"""
Suite of things to work out p&l, and statistics thereof

"""

from copy import copy

import pandas as pd
from pandas.tseries.offsets import BDay
import numpy as np
import scipy

from syscore.algos import robust_vol_calc
from syscore.pdutils import multiply_df_single_column, divide_df_single_column, drawdown
from syscore.dateutils import BUSINESS_DAYS_IN_YEAR, ROOT_BDAYS_INYEAR

def pandl(price=None, trades=None, marktomarket=True, positions=None, delayfill=True, roundpositions=False, 
          price_change_volatility=None, forecast=None, fx=None, value_of_price_point=1.0, 
          return_all=False):
    """
    Calculate pandl for an individual position
    
    If marktomarket=True, and trades is provided, calculate pandl both at open/close and mark to market in between
    
    If trades is not provided, work out using positions. 
           If delayfill is True, assume we get filled at the next price after the trade
    
           If roundpositions is True when working out trades from positions, then round; otherwise assume we trade fractional lots 
    
        If positions are not provided, work out position using forecast and volatility (this will be for an arbitrary daily risk target)
    
             If volatility is not provided, work out from price
    
    If fx is not provided, assume fx rate is 1.0 and work out p&l in currency of instrument
    
    If value_of_price_point is not provided, assume is 1.0 (block size is value of 1 price point, eg 100 if you're buying 100 shares for one instrument block)


    
    :param price: price series
    :type price: Tx1 pd.DataFrame

    :param trades: set of trades done
    :type trades: Tx1 pd.DataFrame or None 

    :param marktomarket: Should we mark to market, or just use traded prices?
    :type marktomarket: bool 

    :param positions: series of positions
    :type positions: Tx1 pd.DataFrame  or None 

    :param delayfill: If calculating trades, should we round positions first?
    :type delayfill: bool 

    :param roundpositions: If calculating trades, should we round positions first?
    :type roundpositions: bool 

    :param price_change_volatility: series of volatility estimates, used for calculation positions
    :type price_change_volatility: Tx1 pd.DataFrame  or None

    :param forecast: series of forecasts, needed to work out positions
    :type forecast: Tx1 pd.DataFrame  or None

    :param fx: series of fx rates from instrument currency to base currency, to work out p&l in base currency
    :type fx: Tx1 pd.DataFrame  or None

    :param value_of_price_point: value of one unit movement in price
    :type value_of_price_point: float

    :param roundpositions: If calculating trades, should we round positions first?
    :type roundpositions: bool 

    
    :returns: if return_all : 4- Tuple (positions, trades, instr_ccy_returns, base_ccy_returns) all Tx1 pd.DataFrames
                            is "":   Tx1 accountCurve
    
    
    """
    if price is None:
        raise Exception("Can't work p&l without price")
        
    if fx is None:
        ## assume it's 1.0
        fx=pd.Series([1.0]*len(price.index), index=price.index).to_frame("fx")
    
    if trades is None:
        get_trades_from_positions(positions, delayfill, roundpositions, price_change_volatility, forecast, fx, value_of_price_point)

    if marktomarket:
        ### want to have both kinds of price
        prices_to_use=pd.concat([price, trades.fill_price], axis=1, join='outer')
        
        ## Where no fill price available, use price
        prices_to_use=prices_to_use.fillna(axis=1, method="ffill")
        
        prices_to_use=prices_to_use.fill_price.to_frame("price")

        ## alight trades
        
        trades_to_use=trades.reindex(prices_to_use.index, fill_value=0.0).trades.to_frame("trades")

    else:
        ### only calculate p&l on trades, using fills
        trades_to_use=trades.trades.to_frame("trades")
        prices_to_use=trades.fill_price.to_frame("price").ffill()

    cum_trades=trades_to_use.cumsum().ffill()
    price_returns=prices_to_use.diff()
    
    instr_ccy_returns=multiply_df_single_column(cum_trades.shift(1), price_returns)*value_of_price_point
    fx=fx.reindex(trades_to_use.index, method="ffill")
    base_ccy_returns=multiply_df_single_column(instr_ccy_returns, fx)

    instr_ccy_returns.columns=["pandl_ccy"]
    base_ccy_returns.columns=["pandl_base"]
    cum_trades.columns=["cum_trades"]
    
    if return_all:
        return (cum_trades, trades, instr_ccy_returns, base_ccy_returns)
    else:
        return accountCurve(base_ccy_returns)
        
def get_trades_from_positions(price, positions, delayfill, roundpositions, price_change_volatility, forecast, fx, value_of_price_point):
    """
    Work out trades implied by a series of positions
       If delayfill is True, assume we get filled at the next price after the trade

       If roundpositions is True when working out trades from positions, then round; otherwise assume we trade fractional lots 

    If positions are not provided, work out position using forecast and volatility (this will be for an arbitrary daily risk target)
    
    If volatility is not provided, work out from price
    
    
    :param price: price series
    :type price: Tx1 pd.DataFrame

    :param positions: series of positions
    :type positions: Tx1 pd.DataFrame  or None 

    :param delayfill: If calculating trades, should we round positions first?
    :type delayfill: bool 

    :param roundpositions: If calculating trades, should we round positions first?
    :type roundpositions: bool 

    :param price_change_volatility: series of volatility estimates, used for calculation positions
    :type price_change_volatility: Tx1 pd.DataFrame  or None

    :param forecast: series of forecasts, needed to work out positions
    :type forecast: Tx1 pd.DataFrame  or None

    :param fx: series of fx rates from instrument currency to base currency, to work out p&l in base currency
    :type fx: Tx1 pd.DataFrame  or None

    :param block_size: value of one movement in price
    :type block_size: float

    
    :returns: Tx1 pd dataframe of trades
    
    """
    
    if positions is None:
        get_positions_from_forecasts(price, price_change_volatility, forecast, fx, value_of_price_point)
       
    if roundpositions:
        ## round to whole positions
        round_positions=positions.round()
    else:
        round_positions=copy(positions)

    ## deal with edge cases where we don't have a zero position initially, or leading nans
    first_row=pd.DataFrame([0.0], index=[round_positions.index[0]-BDay(1)])
    round_positions=pd.concat([first_row, round_positions], axis=0)
    round_positions=round_positions.ffill()

    trades=round_positions.diff()

    if delayfill:
        ## fill will happen one day after we generated trade (being conservative)
        trades.index=trades.index+pd.DateOffset(1)
        
    ## put prices on to correct timestamp
    ans=pd.concat([trades, price], axis=1, join='outer')    
    ans.columns=['trades', 'fill_price']


    ## fill will happen at next valid price if it happens to be missing
    
    ans.fill_price=ans.fill_price.fillna(method="bfill")
    
    ## remove zeros (turns into nans)
    ans=ans[ans.trades!=0.0]
    ans=ans[np.isfinite(ans.trades)]
    
    return ans
        
        
        
def get_positions_from_forecasts(price, price_change_volatility, forecast, fx, value_of_price_point, **kwargs):
    """
    Work out position using forecast, volatility, fx, value_of_price_point (this will be for an arbitrary daily risk target)
    
    If volatility is not provided, work out from price (uses a standard method so may differ from precise system p&l)
    
    :param price: price series
    :type price: Tx1 pd.DataFrame
    
    :param price_change_volatility: series of volatility estimates. NOT % volatility, price difference vol
    :type price_change_volatility: Tx1 pd.DataFrame  or None

    :param forecast: series of forecasts, needed to work out positions
    :type forecast: Tx1 pd.DataFrame 

    :param fx: series of fx rates from instrument currency to base currency, to work out p&l in base currency
    :type fx: Tx1 pd.DataFrame  

    :param value_of_price_point: value of one unit movement in price
    :type value_of_price_point: float

    **kwargs: passed to vol calculation
    
    :returns: Tx1 pd dataframe of positions
    
    """
    if forecast is None:
        raise Exception("If you don't provide a series of trades or positions, I need a forecast")

    if price_change_volatility is None:
        price_change_volatility=robust_vol_calc(price.diff(), **kwargs)

    """
    Herein the proof why this position calculation is correct
    
    Position = forecast x instrument weight x instrument_div_mult x vol_scalar / 10.0
             = forecast x instrument weight x instrument_div_mult x daily cash vol target / (10.0 x                             instr value volatility)
             = forecast x instrument weight x instrument_div_mult x daily cash vol target / (10.0 x                               instr ccy volatility                                                    x fx rate)
             = forecast x instrument weight x instrument_div_mult x daily cash vol target / (10.0 x            block value                              x % price volatility                              x fx rate)
             = forecast x instrument weight x instrument_div_mult x daily cash vol target / (10.0 x underlying price x 0.01 x value of price move x 100 x price diff volatility/(underlying price)        x fx rate)
             = forecast x instrument weight x instrument_div_mult x daily cash vol target / (10.0 x                         x value of price move       x price change volatility                           x fx rate)
    
    Making some arbitrary assumptions (one instrument, 100% of capital, daily target 1 million):
    
             = forecast x 1.0               x 1.0                 x 1,000,000            / (10.0 x                         x value of price move       x price diff volatility                           x fx rate)
             = forecast x  100,000 / (value of price move x price change volatility x fx rate)
    
    """
    fx=fx.reindex(price_change_volatility.index, method="ffill")
    denominator=value_of_price_point * multiply_df_single_column(price_change_volatility,fx, ffill=(False, True))
    
    position = divide_df_single_column(forecast * 100000, denominator, ffill=(True, True))
    position.columns=['position']

    return position

class accountCurve(pd.DataFrame):
    def __init__(self, returns=None, capital=None, **kwargs):
        """
        Create an account curve; from which many lovely statistics can be gathered

        We create eithier by passing returns (a dataframe of returns), or **kwargs which will be used by the pandl function

        If capital is provided (eithier as a float, or dataframe) then % returns will be calculated

        :param returns: series of returns
        :type price: Tx1 pd.DataFrame
        
        :param capital: scaling factor for accounting
        :type capital: None
                       float : fixed scaling will be applied

        FIXME: needs doctest
        """

        if returns is None:
            returns=pandl(**kwargs)
        
        if capital is not None:
            if type(capital) is float:
                returns=returns/capital
            else:
                capital=capital.reindex(returns.index, method="ffill")
                returns=divide_df_single_column(returns, capital)
            
        super(accountCurve, self).__init__(returns)

    def daily(self):
        ## we cache this since it's used so much
        
        if hasattr(self,"_daily_series"):
            return self._daily_series
        else:
            daily_returns=self.resample("1B", how="sum")
            setattr(self, "_daily_series", daily_returns)
            return daily_returns

    def curve(self):
        ## we cache this since it's used so much
        if hasattr(self,"_curve"):
            return self._curve
        else:
            curve=self.cumsum().ffill()
            setattr(self, "_curve", curve)
            return curve

    def weekly(self):
        return self.resample("W", how="sum")


    def monthly(self):
        return self.resample("MS", how="sum")

    def annual(self):
        return self.resample("A", how="sum")

    def ann_daily_mean(self):
        x=self.daily()
        avg=x.mean()
        
        return avg*BUSINESS_DAYS_IN_YEAR
    
    def ann_daily_std(self):
        x=self.daily()
        daily_std=x.std()
        
        return daily_std*ROOT_BDAYS_INYEAR
    
    def sharpe(self):
        mean_return=self.ann_daily_mean()
        vol=self.ann_daily_std()
        
        return mean_return/vol
    
    def drawdown(self):
        x=self.curve()
        return drawdown(x)
    
    def avg_drawdown(self):
        dd=self.drawdown()
        return np.nanmean(dd.values)

    def worst_drawdown(self):
        dd=self.drawdown()
        return np.nanmin(dd.values)
        
    def time_in_drawdown(self):
        dd=self.drawdown()
        dd=[z for z in dd if not np.isnan(z)]
        in_dd=float(len([z for z in dd if z<0]))
        return in_dd/float(len(dd))

    def vals(self):
        x=self.daily()
        x=[z for z in x if not np.isnan(z)]
        return x

    def min(self):
        
        return np.nanmin(self.vals())
    
    def max(self):
        return np.max(self.vals())
    
    def median(self):
        return np.median(self.vals())
    
    def skew(self):
        return scipy.stats.skew(self.vals())
    
    def mean(self):
        x=self.daily()
        return np.nanmean(x)
    
    def losses(self):
        x=self.vals()
        return [z for z in x if z<0]
    
    def gains(self):
        x=self.vals()
        return [z for z in x if z>0]
    
    def avg_loss(self):
        return np.mean(self.losses())

    def avg_gain(self):
        return np.mean(self.gains())
    
        
    def gaintolossratio(self):
        return self.avg_gain()/-self.avg_loss()
    
    def profitfactor(self):
        return sum(self.gains())/-sum(self.losses())
    
    def hitrate(self):
        no_gains=float(len(self.gains()))
        no_losses=float(len(self.losses()))
        return no_gains/(no_losses+no_gains)
    
    def rolling_ann_std(self, window=40):
        x=self.daily()
        y=pd.rolling_std(x, window, min_periods=4, center=True)
        return y*ROOT_BDAYS_INYEAR

        
if __name__ == '__main__':
    import doctest
    doctest.testmod()
