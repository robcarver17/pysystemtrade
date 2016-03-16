"""
Suite of things to work out p&l, and statistics thereof

"""

from copy import copy

import pandas as pd
from pandas.tseries.offsets import BDay
import numpy as np
from scipy.stats import skew, ttest_rel, ttest_1samp
import scipy.stats as stats
import random

from syscore.algos import robust_vol_calc
from syscore.pdutils import add_df_single_column, multiply_df_single_column, divide_df_single_column, drawdown, index_match
from syscore.dateutils import BUSINESS_DAYS_IN_YEAR, ROOT_BDAYS_INYEAR, WEEKS_IN_YEAR, ROOT_WEEKS_IN_YEAR
from syscore.dateutils import MONTHS_IN_YEAR, ROOT_MONTHS_IN_YEAR



def account_test(ac1, ac2):
    """
    Given two Account like objects performs a two sided t test
    """
    
    common_ts=list(set(list(ac1.index)) & set(list(ac2.index)))
    common_ts.sort()
    
    ac1_common=ac1.cumsum().reindex(common_ts, method="ffill").diff().values
    ac2_common=ac2.cumsum().reindex(common_ts, method="ffill").diff().values
    
    missing_values=[idx for idx in range(len(common_ts)) 
                    if (np.isnan(ac1_common[idx]) or np.isnan(ac2_common[idx]))]
    ac1_common=[ac1_common[idx] for idx in range(len(common_ts)) if idx not in missing_values]
    ac2_common=[ac2_common[idx] for idx in range(len(common_ts)) if idx not in missing_values]

    return ttest_rel(ac1_common, ac2_common)

"""
some defaults
"""
CAPITAL = 10000000.0
ANN_RISK_TARGET = 0.16
DAILY_CAPITAL=CAPITAL * ANN_RISK_TARGET / ROOT_BDAYS_INYEAR

"""


"""


def pandl_with_data(price, trades=None, marktomarket=True, positions=None,
          delayfill=True, roundpositions=False,
          get_daily_returns_volatility=None, forecast=None, fx=None,
          capital=None, ann_risk_target=None,
          value_of_price_point=1.0):
    
    """
    Calculate pandl for an individual position

    If marktomarket=True, and trades is provided, calculate pandl both at
    open/close and mark to market in between

    If trades is not provided, work out using positions. If delayfill is True,
           assume we get filled at the next price after the trade

           If roundpositions is True when working out trades from positions,
           then round; otherwise assume we trade fractional lots

        If positions are not provided, work out position using forecast and
        volatility (this will be for an arbitrary daily risk target)

        If volatility is not provided, work out from price

    If fx is not provided, assume fx rate is 1.0 and work out p&l in currency
        of instrument

    If value_of_price_point is not provided, assume is 1.0 (block size is value
    of 1 price point, eg 100 if you're buying 100 shares for one instrument
    block)

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

    :param roundpositions: If calculating trades, should we round positions
        first?
    :type roundpositions: bool

    :param get_daily_returns_volatility: series of volatility estimates, used
        for calculation positions
    :type get_daily_returns_volatility: Tx1 pd.DataFrame  or None

    :param forecast: series of forecasts, needed to work out positions
    :type forecast: Tx1 pd.DataFrame  or None

    :param fx: series of fx rates from instrument currency to base currency, to
        work out p&l in base currency
    :type fx: Tx1 pd.DataFrame  or None

    :param value_of_price_point: value of one unit movement in price
    :type value_of_price_point: float

    :param roundpositions: If calculating trades, should we round positions first?
    :type roundpositions: bool

    :param weighting: Weighting scheme to multiply trades by (and thus returns)
    :type weighting: pd.DataFrame 

    :returns: 5- Tuple (positions, trades, instr_ccy_returns,
                            base_ccy_returns, fx) all Tx1 pd.DataFrames

    """
    if price is None:
        raise Exception("Can't work p&l without price")

    if fx is None:
        # assume it's 1.0
        fx = pd.Series([1.0] * len(price.index),
                       index=price.index).to_frame("fx")

    if trades is None:
        trades = get_trades_from_positions(price,
                                           positions,
                                           delayfill,
                                           roundpositions,
                                           get_daily_returns_volatility,
                                           forecast,
                                           fx,
                                           value_of_price_point,
                                           capital,
                                           ann_risk_target)


    if marktomarket:
        # want to have both kinds of price
        prices_to_use = pd.concat(
            [price, trades.fill_price], axis=1, join='outer')

        # Where no fill price available, use price
        prices_to_use = prices_to_use.fillna(axis=1, method="ffill")

        prices_to_use = prices_to_use.fill_price.to_frame("price")

        # alight trades

        trades_to_use = trades.reindex(
            prices_to_use.index, fill_value=0.0).trades.to_frame("trades")

    else:
        # only calculate p&l on trades, using fills
        trades_to_use = trades.trades.to_frame("trades")
        prices_to_use = trades.fill_price.to_frame("price").ffill()


    cum_trades = trades_to_use.cumsum().ffill()

    price_returns = prices_to_use.diff()

    instr_ccy_returns = multiply_df_single_column(
        cum_trades.shift(1), price_returns) * value_of_price_point
    
    instr_ccy_returns=instr_ccy_returns.resample("1B", how="sum")
        
    fx = fx.reindex(instr_ccy_returns.index, method="ffill")
    base_ccy_returns = multiply_df_single_column(instr_ccy_returns, fx)

    instr_ccy_returns.columns = ["pandl_ccy"]
    base_ccy_returns.columns = ["pandl_base"]
    cum_trades.columns = ["cum_trades"]

    return (cum_trades, trades, instr_ccy_returns,
            base_ccy_returns, fx, value_of_price_point)


def get_trades_from_positions(price,
                              positions,
                              delayfill,
                              roundpositions,
                              get_daily_returns_volatility,
                              forecast,
                              fx,
                              value_of_price_point,
                              capital,
                              ann_risk_target):
    """
    Work out trades implied by a series of positions
       If delayfill is True, assume we get filled at the next price after the
       trade

       If roundpositions is True when working out trades from positions, then
       round; otherwise assume we trade fractional lots

    If positions are not provided, work out position using forecast and
    volatility (this will be for an arbitrary daily risk target)

    If volatility is not provided, work out from price


    Args:
        price (Tx1 pd.DataFrame): price series

        positions (Tx1 pd.DataFrame or None): (series of positions)

        delayfill (bool): If calculating trades, should we round positions
            first?

        roundpositions (bool): If calculating trades, should we round positions
            first?

        get_daily_returns_volatility (Tx1 pd.DataFrame or None): series of
            volatility estimates, used for calculation positions

        forecast (Tx1 pd.DataFrame or None): series of forecasts, needed to
            work out positions

        fx (Tx1 pd.DataFrame or None): series of fx rates from instrument
            currency to base currency, to work out p&l in base currency

        block_size (float): value of one movement in price

    Returns:
        Tx1 pd dataframe of trades

    """

    if positions is None:
        positions = get_positions_from_forecasts(price,
                                                 get_daily_returns_volatility,
                                                 forecast,
                                                 fx,
                                                 value_of_price_point,
                                                 capital,
                                                 ann_risk_target)

    if roundpositions:
        # round to whole positions
        round_positions = positions.round()
    else:
        round_positions = copy(positions)

    # deal with edge cases where we don't have a zero position initially, or
    # leading nans
    first_row = pd.DataFrame([0.0], index=[round_positions.index[0] - BDay(1)])
    first_row.columns = round_positions.columns
    round_positions = pd.concat([first_row, round_positions], axis=0)
    round_positions = round_positions.ffill()

    trades = round_positions.diff()

    if delayfill:
        # fill will happen one day after we generated trade (being
        # conservative)
        trades.index = trades.index + pd.DateOffset(1)

    # put prices on to correct timestamp
    ans = index_match(trades, price, ffill=(False, True))
    ans.columns = ['trades', 'fill_price']

    # fill will happen at next valid price if it happens to be missing
    ans.fill_price = ans.fill_price.fillna(method="bfill")

    # remove zeros (turns into nans)
    ans = ans[ans.trades != 0.0]
    ans = ans[np.isfinite(ans.trades)]

    return ans


def get_positions_from_forecasts(price, get_daily_returns_volatility, forecast,
                                 fx, value_of_price_point, capital,
                                 ann_risk_target, **kwargs):
    """
    Work out position using forecast, volatility, fx, value_of_price_point
    (this will be for an arbitrary daily risk target)

    If volatility is not provided, work out from price (uses a standard method
    so may differ from precise system p&l)

    :param price: price series
    :type price: Tx1 pd.DataFrame

    :param get_daily_returns_volatility: series of volatility estimates. NOT %
    volatility, price difference vol
    :type get_daily_returns_volatility: Tx1 pd.DataFrame  or None

    :param forecast: series of forecasts, needed to work out positions
    :type forecast: Tx1 pd.DataFrame

    :param fx: series of fx rates from instrument currency to base currency, to
    work out p&l in base currency
    :type fx: Tx1 pd.DataFrame

    :param value_of_price_point: value of one unit movement in price
    :type value_of_price_point: float

    **kwargs: passed to vol calculation

    :returns: Tx1 pd dataframe of positions

    """
    if forecast is None:
        raise Exception(
            "If you don't provide a series of trades or positions, I need a "
            "forecast")

    if get_daily_returns_volatility is None:
        get_daily_returns_volatility = robust_vol_calc(price.diff(), **kwargs)

    """
    Herein the proof why this position calculation is correct (see chapters
    5-11 of 'systematic trading' book)

    Position = forecast x instrument weight x instrument_div_mult x vol_scalar / 10.0
             = forecast x instrument weight x instrument_div_mult x daily cash vol target / (10.0 x instr value volatility)
             = forecast x instrument weight x instrument_div_mult x daily cash vol target / (10.0 x instr ccy volatility x fx rate)
             = forecast x instrument weight x instrument_div_mult x daily cash vol target / (10.0 x block value x % price volatility x fx rate)
             = forecast x instrument weight x instrument_div_mult x daily cash vol target / (10.0 x underlying price x 0.01 x value of price move x 100 x price change volatility/(underlying price) x fx rate)
             = forecast x instrument weight x instrument_div_mult x daily cash vol target / (10.0 x value of price move x price change volatility x fx rate)

    Making some arbitrary assumptions (one instrument, 100% of capital, daily target DAILY_CAPITAL):

             = forecast x 1.0 x 1.0 x DAILY_CAPITAL / (10.0 x value of price move x price diff volatility x fx rate)
             = forecast x  multiplier / (value of price move x price change volatility x fx rate)
    """
    (Unused_capital, daily_capital) = resolve_capital(forecast, capital, ann_risk_target)
    multiplier = daily_capital * 1.0 * 1.0 / 10.0
    fx = fx.reindex(get_daily_returns_volatility.index, method="ffill")

    denominator = (value_of_price_point *
                   multiply_df_single_column(get_daily_returns_volatility,
                                             fx,
                                             ffill=(False, True)))

    numerator = multiply_df_single_column(forecast, multiplier, ffill=(False,True))

    position = divide_df_single_column(numerator,
                                       denominator,
                                       ffill=(True, True))
    position.columns = ['position']
    return position

    


class accountCurveSingleElementOneFreq(pd.DataFrame):
    """
    A single account curve for one asset (instrument / trading rule variation, ...)
     and one part of it (gross, net, costs)
     and for one frequency (daily, weekly, monthly...)
    
    Inherits from data frame

    We never init these directly but only as part of accountCurveSingleElement
    
    """
    def __init__(self, returns_df, weighted_flag=False, frequency="D", name="account"):
        """
        :param returns_df: series of returns
        :type returns_df: Tx1 pd.DataFrame

        :param frequency: Frequency D days, W weeks, M months, Y years
        :type frequency: str

        """
        returns_df.columns=[name]
        super().__init__(returns_df)
        
        try:
            returns_scalar=dict(D=BUSINESS_DAYS_IN_YEAR, W=WEEKS_IN_YEAR,
                                M=MONTHS_IN_YEAR, Y=1)[frequency]
                                
            vol_scalar=dict(D=ROOT_BDAYS_INYEAR, W=ROOT_WEEKS_IN_YEAR,
                                M=ROOT_MONTHS_IN_YEAR, Y=1)[frequency]
            
        except KeyError:
            raise Exception("Not a frequency %s" % frequency)
        
        setattr(self, "frequency", frequency)
        setattr(self, "_returns_scalar", returns_scalar)
        setattr(self, "_vol_scalar", vol_scalar)
        setattr(self, "_account_name", name)
        setattr(self, "_returns_df", returns_df)
        setattr(self, "weighted_flag", weighted_flag)

    def as_df(self):
        return pd.DataFrame(self._returns_df)

    def curve(self):
        # we cache this since it's used so much
        if hasattr(self, "_curve"):
            return self._curve
        else:
            curve = self.cumsum().ffill()
            setattr(self, "_curve", curve)
            return curve

    def mean(self):
        return float(self.as_df().mean())
    
    def std(self):
        return float(self.as_df().std())

    def ann_mean(self):
        avg = self.mean()

        return avg * self._returns_scalar

    def ann_std(self):
        period_std = self.std()

        return period_std * self._vol_scalar


    def sharpe(self):
        mean_return = self.ann_mean()
        vol = self.ann_std()
        try:
            sharpe=mean_return / vol
        except ZeroDivisionError:
            sharpe=np.nan
        return sharpe

    def drawdown(self):
        x = self.curve()
        return drawdown(x)

    def avg_drawdown(self):
        dd = self.drawdown()
        return np.nanmean(dd.values)

    def worst_drawdown(self):
        dd = self.drawdown()
        return np.nanmin(dd.values)

    def time_in_drawdown(self):
        dd = self.drawdown()
        dd = [z[0] for z in dd.values if not np.isnan(z[0])]
        in_dd = float(len([z for z in dd if z < 0]))
        return in_dd / float(len(dd))

    def calmar(self):
        return self.ann_mean() / -self.worst_drawdown()

    def avg_return_to_drawdown(self):
        return self.ann_mean() / -self.avg_drawdown()

    def sortino(self):
        period_stddev = np.std(self.losses())

        ann_stdev = period_stddev * self._vol_scalar
        ann_mean = self.ann_mean()

        try:
            sortino=ann_mean / ann_stdev
        except ZeroDivisionError:
            sortino=np.nan

        return sortino

    def vals(self):
        x = [z[0] for z in self.values if not np.isnan(z[0])]
        return x

    def min(self):

        return np.nanmin(self.vals())

    def max(self):
        return np.max(self.vals())

    def median(self):
        return np.median(self.vals())

    def skew(self):
        return skew(self.vals())

    def losses(self):
        x = self.vals()
        return [z for z in x if z < 0]

    def gains(self):
        x = self.vals()
        return [z for z in x if z > 0]

    def avg_loss(self):
        return np.mean(self.losses())

    def avg_gain(self):
        return np.mean(self.gains())

    def gaintolossratio(self):
        return self.avg_gain() / -self.avg_loss()

    def profitfactor(self):
        return sum(self.gains()) / -sum(self.losses())

    def hitrate(self):
        no_gains = float(len(self.gains()))
        no_losses = float(len(self.losses()))
        return no_gains / (no_losses + no_gains)

    def rolling_ann_std(self, window=40):
        y = pd.rolling_std(self.as_df(), window, min_periods=4, center=True).to_frame()
        return y * self._vol_scalar

    def t_test(self):
        return ttest_1samp(self.vals(), 0.0)

    def stats(self):

        stats_list = ["min", "max", "median", "mean", "std", "skew",
                      "ann_mean", "ann_std", "sharpe", "sortino",
                      "avg_drawdown", "time_in_drawdown",
                      "calmar", "avg_return_to_drawdown",
                      "avg_loss", "avg_gain", "gaintolossratio", "profitfactor", "hitrate"]

        build_stats = []
        for stat_name in stats_list:
            stat_method = getattr(self, stat_name)
            ans = stat_method()
            build_stats.append((stat_name, "{0:.4g}".format(ans)))

        comment1 = ("You can also plot:", [
                    "rolling_ann_std", "drawdown", "curve"])

        return [build_stats, comment1]

    def __repr__(self):
        if self.weighted_flag:
            weight_comment="Weighted"
        else:
            weight_comment="Unweighted"
        return super().__repr__()+"\n %s account curve; use object.stats() to see methods" % weight_comment
    


class accountCurveSingleElement(accountCurveSingleElementOneFreq):
    """
    A single account curve for one asset (instrument / trading rule variation, ...)
     and one part of it (gross, net, costs)
    
    Inherits from data frame

    We never init these directly but only as part of accountCurveSingle
    
    """
    
    def __init__(self, returns_df, weighted_flag=False, name="account"):
        """
        :param returns_df: series of returns
        :type returns_df: Tx1 pd.DataFrame

        """
        ## We often want to use  
        daily_returns = returns_df.resample("1B", how="sum")
        weekly_returns=returns_df.resample("W", how="sum")
        monthly_returns=returns_df.resample("MS", how="sum")
        annual_returns=returns_df.resample("A", how="sum")
        
        super().__init__(daily_returns, frequency="D", name=name, weighted_flag=weighted_flag)

        setattr(self, "daily", accountCurveSingleElementOneFreq(daily_returns, frequency="D", name=name, weighted_flag=weighted_flag))
        setattr(self, "weekly", accountCurveSingleElementOneFreq(weekly_returns, frequency="W", name=name, weighted_flag=weighted_flag))
        setattr(self, "monthly", accountCurveSingleElementOneFreq(monthly_returns, frequency="M", name=name, weighted_flag=weighted_flag))
        setattr(self, "annual", accountCurveSingleElementOneFreq(annual_returns, frequency="Y", name=name, weighted_flag=weighted_flag))

    def __repr__(self):
        return super().__repr__()+ "\n Use object.freq.method() to access periods (freq=daily, weekly, monthly, annual) default: daily"




class accountCurveSingle(accountCurveSingleElement):
    """
    A single account curve for one asset (instrument / trading rule variation, ...)
    
    Inherits from data frame
    
    On the surface we see the 'net' but there's also a gross and cost part included
    
    """
    def __init__(self, gross_returns, net_returns, costs, weighted_flag=False):

        
        super().__init__(net_returns,  weighted_flag=weighted_flag)
        
        setattr(self, "net", accountCurveSingleElement(net_returns, name="net", weighted_flag=weighted_flag))
        setattr(self, "gross", accountCurveSingleElement(gross_returns, name="gross", weighted_flag=weighted_flag))
        setattr(self, "costs", accountCurveSingleElement(costs, name="costs", weighted_flag=weighted_flag))

    def __repr__(self):
        return super().__repr__()+"\n Use object.curve_type.freq.method() (freq=net, gross, costs) default: net"
                
    def to_ncg_frame(self):
        
        ans=pd.concat([self.net.as_df(), self.gross.as_df(), self.costs.as_df()], axis=1)
        ans.columns=["net", "gross", "costs"]
        
        return ans

class accountCurve(accountCurveSingle):

    def __init__(self, price,  percentage=False, cash_costs=None, SR_cost=None, 
                 capital=None, ann_risk_target=None, weighting=None, weighted_flag=False,
                 **kwargs):
        """
        Create an account curve; from which many lovely statistics can be gathered
        
        
        We create by passing **kwargs which will be used by the pandl function
        
        :param percentage: Return % returns, or base currency if False
        :type percentage: bool
        
        :param cash_cost: Cost in local currency units per instrument block 
        :type cash_cost: float
        
        :param SR_cost: Cost in annualised Sharpe Ratio units (0.01 = 0.01 SR)
        :type SR_cost: float
        
        Note if both are included then cash_cost will be disregarded
        
        :param capital: Capital at risk. Used for % returns, and calculating daily risk for SR costs  
        :type capital: float or Tx1 
        
        :param ann_risk_target: Annual risk target, as % of capital. Used to calculate daily risk for SR costs
        :type ann_risk_target: float
        
        **kwargs  passed to profit and loss calculation
         (price, trades, marktomarket, positions,
          delayfill, roundpositions,
          get_daily_returns_volatility, forecast, fx,
          value_of_price_point)
        
        """

        returns_data=pandl_with_data(price,  capital=capital, ann_risk_target=ann_risk_target, **kwargs)

        (cum_trades, trades, instr_ccy_returns,
            base_ccy_returns, fx, value_of_price_point)=returns_data
            
        gross_returns=base_ccy_returns

        ## always returns a time series
        (capital, daily_capital)=resolve_capital(gross_returns, capital, ann_risk_target)

        (costs_base_ccy, costs_instr_ccy)=calc_costs(returns_data, cash_costs, SR_cost, daily_capital)

        net_returns=add_df_single_column(gross_returns,costs_base_ccy) ## costs are negative returns
        
        if weighting is not None:
            net_returns = multiply_df_single_column(
                net_returns, weighting, ffill=(False, True))
            
            gross_returns = multiply_df_single_column(
                gross_returns, weighting, ffill=(False, True))
            
            costs_base_ccy = multiply_df_single_column(
                costs_base_ccy, weighting, ffill=(False, True))
            
        perc_gross_returns = divide_df_single_column(
            gross_returns, capital)
        
        perc_costs=divide_df_single_column(
            costs_base_ccy, capital)

        perc_net_returns=add_df_single_column(perc_gross_returns, perc_costs)

        if percentage:
            super().__init__(perc_gross_returns, perc_net_returns, perc_costs, weighted_flag=weighted_flag)
        else:
            super().__init__(gross_returns, net_returns, costs_base_ccy, weighted_flag=weighted_flag)
            
        setattr(self, "cum_trades", cum_trades)
        setattr(self, "trades", trades)
        setattr(self, "instr_ccy_returns", instr_ccy_returns)
        setattr(self, "base_ccy_returns", base_ccy_returns)
        setattr(self, "fx", fx)
        
        setattr(self, "capital", capital)
        setattr(self, "daily_capital", daily_capital)
        
        setattr(self, "costs_instr_ccy", costs_instr_ccy)
        setattr(self, "costs_base_ccy", costs_base_ccy)
            
        setattr(self, "ccy_returns", 
                accountCurveSingle(gross_returns, net_returns, costs_base_ccy))
        setattr(self, "perc_returns", 
                accountCurveSingle(perc_gross_returns, perc_net_returns, perc_costs))
        

    def __repr__(self):
        return super().__repr__()+ "\n Use object.calc_data() to see calculation details"

    def calc_data(self):
        calc_items=["cum_trades",  "trades",  "instr_ccy_returns",  "base_ccy_returns",  
                    "fx", "capital",  "daily_capital", "costs_instr_ccy",  "costs_base_ccy", 
                     "ccy_returns",  "perc_returns"]
        
        calc_dict=dict([(calc_name, getattr(self, calc_name)) for calc_name in calc_items])
        
        return calc_dict
        
def calc_costs(returns_data, cash_costs, SR_cost, daily_capital):
    """
    Calculate costs
    
    :param returns_data: returns data
    :type returns_data: 5 tuple returned by pandl data function
    
    :param cash_costs: Cost in local currency units per instrument block 
    :type cash_costs: 3 tuple of floats; value_total_per_block, value_of_pertrade_commission, percentage_cost
    
    :param SR_cost: Cost in annualised Sharpe Ratio units (0.01 = 0.01 SR)
    :type SR_cost: float

    Set to None if not using. If both included use SR_cost
    
    :param daily_capital: Capital at risk each day. Used for SR calculations
    :type daily_capital: Tx1 pd.DataFrame
    
    :returns : Tx1 pd.DataFrame of costs. Minus numbers are losses
    
    """

    (cum_trades, trades, instr_ccy_returns,
        base_ccy_returns, fx, value_of_price_point)=returns_data

    if SR_cost is not None:
        ## use SR_cost
        ann_risk = daily_capital*ROOT_BDAYS_INYEAR
        ann_cost = -SR_cost*ann_risk
        
        costs_instr_ccy = ann_cost/BUSINESS_DAYS_IN_YEAR
    
    elif cash_costs is not None:
        ## use cost per blocks
        
        (value_total_per_block, value_of_pertrade_commission, percentage_cost)=cash_costs

        trades=trades['trades'].abs()
        trades_in_blocks=trades.resample("1B", how="sum").to_frame()
        costs_blocks = - trades_in_blocks*value_total_per_block

        value_of_trades=trades_in_blocks * value_of_price_point
        costs_percentage = percentage_cost * value_of_trades
        
        traded=trades[trades>0]
        
        if len(traded)==0:
            costs_pertrade = pd.DataFrame([0.0]*len(cum_trades.index), cum_trades.index)
        else:
            costs_pertrade = pd.DataFrame([value_of_pertrade_commission]*len(traded.index), traded.index)
            costs_pertrade = costs_pertrade.reindex(trades.index)
        
        costs_instr_ccy = add_df_single_column(costs_blocks, add_df_single_column(costs_percentage, costs_pertrade))
        
    else:
        ## set costs to zero
        costs_instr_ccy=pd.DataFrame([0.0]*base_ccy_returns.shape[0], index=base_ccy_returns.index)
    
    costs_base_ccy=multiply_df_single_column(costs_instr_ccy, fx, ffill=(False, True))
    costs_base_ccy[np.isnan(costs_base_ccy)]=0.0

    return (costs_base_ccy, costs_instr_ccy)

def resolve_capital(ts_to_scale_to, capital, ann_risk_target):
    """
    Resolve and setup capital
    We need capital for % returns and possibly for SR stuff

    :param ts_to_scale_to: If capital is fixed, what to scale it o  
    :type capital: Tx1 pd.DataFrame
    
    :param capital: Capital at risk. Used for % returns, and calculating daily risk for SR costs  
    :type capital: int, float or Tx1 pd.DataFrame
    
    :param ann_risk_target: Annual risk target, as % of capital. Used to calculate daily risk for SR costs
    :type ann_risk_target: float
    
    :returns tuple: 2 tuple of Tx1 pd.DataFrame

    """
    if capital is None:
        capital=CAPITAL
        
    if type(capital) is float or type(capital) is int:
        capital=pd.DataFrame([capital]*ts_to_scale_to.shape[0], index=ts_to_scale_to.index)
    
    if ann_risk_target is None:
        ann_risk_target=ANN_RISK_TARGET
        
    daily_capital = capital * ann_risk_target / ROOT_BDAYS_INYEAR
    
    return (capital, daily_capital)


def acc_list_to_pd_frame(list_of_ac_curves, columns):
    """
    
    Returns a pandas data frame
    """
    list_of_df=[acc.as_df() for acc in list_of_ac_curves]
    ans=pd.concat(list_of_df, axis=1,  join="outer")
    
    ans.columns=columns
    ans=ans.cumsum().ffill().diff()
    
    return ans


def total_from_list(list_of_ac_curves, columns, name):
    """
    
    Return a single accountCurveSingleElement whose returns are the total across the portfolio
    """
    pdframe=acc_list_to_pd_frame(list_of_ac_curves, columns)
    
    ## all on daily freq so just add up
    totalac=pdframe.sum(axis=1)
    ans=accountCurveSingleElement(totalac, name)
    
    return ans
    

class accountCurveGroupForType(accountCurveSingleElement):
    """
    an accountCurveGroup for one cost type (gross, net, costs)
    """
    def __init__(self, acc_curve_for_type_list, asset_columns, weighted_flag=False, curve_type="net"):
        """
        Create a group of account curves from a list and some column names
        
        looks like accountCurveSingleElement; outward facing is the total p&L
        
        so acc=accountCurveGroupForType()
        acc.mean() ## for the total
        
        Also you can access a instrument (gives an accountCurveSingleElement for an instrument): 
           acc[instrument_code].mean(), acc[instrument_code].mean()
           acc.instrument_code.gross.daily.stats()  
        
        acc.to_frame() ## returns a data frame 

        If you want the original list back:
        
        acc.to_list

        Also: eg acc.get_stats("mean", freq="daily")
        ... Returns a dict of stats 
        
        """
        acc_total=total_from_list(acc_curve_for_type_list, asset_columns, name="total_%s" % curve_type)
        
        super().__init__(acc_total, weighted_flag=weighted_flag)
        
        setattr(self, "to_list", acc_curve_for_type_list)
        setattr(self, "asset_columns", asset_columns)
        setattr(self, "curve_type", curve_type)



    def _getitem_column(self, colname):
        """
        Overriding this method to access individual curves
        
        Returns an object of type accountCurve
        """

        try:
            ans=self.to_list[self.asset_columns.index(colname)]
        except ValueError:
            raise Exception("%s not found in account curve" % colname)
        
        return ans

    def to_frame(self):
        """
        Returns as a data frame
        """
        
        return acc_list_to_pd_frame(self.to_list, self.asset_columns)


    def get_stats(self, stat_method, freq="daily"):
        """
        Returns a stats_dict, one value per asset
        """
        
        return statsDict(self, stat_method, freq)
    
    def time_weights(self):
        """
        Returns a dict, values are weights
        """
        def _len_nonzero(ac_curve):
            return_df=ac_curve.as_df()
            ans=len([x for x in return_df.values if not np.isnan(x)])
            
            return ans
            
        time_weights_dict=dict([(asset_name, _len_nonzero(ac_curve)) for (asset_name, ac_curve) 
                  in zip(self.asset_columns, self.to_list)])
        
        total_weight=sum(time_weights_dict.values())
        
        time_weights_dict = dict([(asset_name, weight/total_weight) for (asset_name, weight) 
                                  in time_weights_dict.items()])
        
        return time_weights_dict

    
class statsDict(dict):
    def __init__(self, acgroup_for_type, stat_method, freq="daily"):
        column_names=acgroup_for_type.asset_columns

        def _get_stat_from_acobject(acobject, stat_method, freq):
            
            freq_obj=getattr(acobject, freq)
            stat_method_function=getattr(freq_obj, stat_method)
            
            return stat_method_function()
        
        dict_values=[(col_name, _get_stat_from_acobject(acgroup_for_type[col_name], stat_method, freq)) 
                  for col_name in column_names]

        super().__init__(dict_values)
        
        ## We need to augment this with time weightings, in case they are needed
                      
        setattr(self, "time_weightings", acgroup_for_type.time_weights())
    
    def weightings(self, timeweighted=False):
        """
        Returns a dict of weightings
        
        Eithier equal weighting, or returns time_weightings
        """
        
        if timeweighted:
            return self.time_weightings
        else:
            return dict([(asset_name, 1.0/len(self.values())) for asset_name in self.keys()])
            
    
    def mean(self, timeweighted=False):
        wts=self.weightings(timeweighted)
        ans=sum([asset_value*wts[asset_name] for (asset_name, asset_value) in self.items()])
        
        return ans
    
    def std(self, timeweighted=False):
        wts=self.weightings(timeweighted)
        avg=self.mean(timeweighted)
        ans=sum([ wts[asset_name] * (asset_value - avg)**2 
                 for (asset_name, asset_value) in self.items()])**.5
        
        return ans
    
    def tstat(self, timeweighted=False):
        t_mean=self.mean(timeweighted)
        t_std=self.std(timeweighted)
        
        if t_std==0.0:
            return np.nan
        
        return t_mean / t_std
    
    def pvalue(self, timeweighted=False):
        tstat=self.tstat(timeweighted)
        n=len(self.values())
        
        if np.isnan(tstat) or n<2:
            return np.nan
        
        pvalue=stats.t.sf(np.abs(tstat), n-1) ## one sided t statistic

        return pvalue
        
class accountCurveGroup(accountCurveSingleElement):
    def __init__(self, acc_curve_list, asset_columns, weighted_flag=False):
        """
        Create a group of account curves from a list and some column names
        
        looks like accountCurve, so outward facing is the total p&L
        FIXME: (need a way to pass the total into accountCurve,
        as series of accountCurveSingle)
        
        so acc=accountCurveGroup()
        acc.mean() 
        acc.net.mean()
        acc.net.daily.mean()
        
        Also you can access a instrument: 
           acc[instrument_code].mean(), acc[instrument_code].net.mean()
           acc.instrument_code.gross.daily.stats()  
        
        acc.to_frame() ## returns a data frame
        acc.to_frame("gross") ## returns a data frame
        acc.costs.to_frame() ## returns a data frame

        If you want the original list back:
        
        acc.to_list

        Also: eg acc.get_stats("mean", curve_type="net", freq="daily")
        acc.net.get_stats("sharpe", freq="weekly") 
        ... Returns a list of stats 
        
        """
        
        net_list=[getattr(x, "net") for x in acc_curve_list]
        gross_list=[getattr(x, "gross") for x in acc_curve_list]
        costs_list=[getattr(x, "costs") for x in acc_curve_list]
        
        acc_list_net=accountCurveGroupForType(net_list, asset_columns=asset_columns, weighted_flag=weighted_flag, 
                                              curve_type="net")

        acc_list_gross=accountCurveGroupForType(gross_list, asset_columns=asset_columns,  weighted_flag=weighted_flag, 
                                                curve_type="gross")

        acc_list_costs=accountCurveGroupForType(costs_list, asset_columns=asset_columns,  weighted_flag=weighted_flag,
                                                curve_type="costs")

        acc_total=total_from_list(net_list, asset_columns, "total")
        
        super().__init__(acc_total,  weighted_flag=weighted_flag)
        
        setattr(self, "net", acc_list_net)
        setattr(self, "gross", acc_list_gross)
        setattr(self, "costs", acc_list_costs)

        setattr(self, "to_list", acc_curve_list)
        setattr(self, "asset_columns", asset_columns)

    def __repr__(self):
        return super().__repr__()+"\n Multiple curves. Use object.curve_type (curve_type= net, gross, costs)" +              "\n Useful methods: to_list, asset_columns(), get_stats(), to_frame()"


    def _getitem_column(self, colname):
        """
        Overriding this method to access individual curves
        
        Returns an object of type accountCurve
        """
        try:
            ans=self.to_list[self.asset_columns.index(colname)]
        except ValueError:
            raise Exception("%s not found in account curve" % colname)
        
        return ans

    def get_stats(self, stat_method, curve_type="net", freq="daily"):
        """
        Returns a dict of stats, one per asset
        """
        
        subobject=getattr(self, curve_type)
        
        return subobject.get_stats(stat_method, freq=freq)

    def to_frame(self, curve_type="net"):
        """
        Returns as a data frame
        
        Defaults to net
        """
        
        actype=getattr(self, curve_type)
        
        return actype.to_frame()

        
    def stack(self):
        """
        Collapse instrument level data into a list of returns in a stack_returns object (pd.TimeSeries)
        
        We can bootstrap this or perform other statistics
        """
        
        returnsStack(self.to_list)


    def to_ncg_frame(self):

        ans=pd.concat([self.net.as_df(), self.gross.as_df(), self.costs.as_df()], axis=1)
        ans.columns=["net", "gross", "costs"]
        
        return ans
        

        
class returnsStack(accountCurveSingle):
    """
    Create a stack of returns which we can bootstrap
    """
    def __init__(self, returns_list):
        
        ## Collapse indices to a single one
        bs_index_to_use=[list(returns.index) for returns in returns_list]
        bs_index_to_use=sum(bs_index_to_use, [])
        bs_index_to_use=list(set(bs_index_to_use))
        
        bs_index_to_use.sort()

        ## Collapse return lists
        curve_type_list =["gross", "net", "costs"]
        
        def _collapse_one_curve_type(returns_list, curve_type):
            collapsed_values = sum(
               
                           [list(getattr(returns, curve_type).iloc[:,0].values) 
                            for returns in returns_list]
               
                                , [])
            
            
            return collapsed_values
        
        collapsed_curves_values=dict([(curve_type, _collapse_one_curve_type(returns_list, curve_type))
                                        for curve_type in curve_type_list])
        
        
        ## We set this to an arbitrary index so we can make an account curve

        gross_returns_df=pd.DataFrame(collapsed_curves_values["gross"], 
                        pd.date_range(start=bs_index_to_use[0], periods=len(collapsed_curves_values["gross"]), freq="B"))

        net_returns_df=pd.DataFrame(collapsed_curves_values["net"], 
                        pd.date_range(start=bs_index_to_use[0], periods=len(collapsed_curves_values["net"]), freq="B"))

        costs_returns_df=pd.DataFrame(collapsed_curves_values["costs"], 
                        pd.date_range(start=bs_index_to_use[0], periods=len(collapsed_curves_values["costs"]), freq="B"))
        
        super().__init__(gross_returns_df, net_returns_df, costs_returns_df)

        ## We need to store this for bootstrapping purposes
        setattr(self, "_bs_index_to_use", bs_index_to_use)


    def bootstrap(self, no_runs=50, length=None):
        """
        Create an accountCurveGroup object containing no_runs, each same length as the
          original portfolio (unless length is set)
        """
        values_to_sample_from=dict(gross=list(getattr(self, "gross").iloc[:,0].values),
                                   net=list(getattr(self, "net").iloc[:,0].values),
                                   costs=list(getattr(self, "costs").iloc[:,0].values))
        
        size_of_bucket=len(self.index)
        
        if length is None:
            index_to_use=self._bs_index_to_use
            length=len(index_to_use)
            
        else:
            index_to_use=pd.date_range(start=self._bs_index_to_use[0], periods=length, freq="B")
        
        bs_list=[]
        for notUsed in range(no_runs):
            sample=[int(round(random.uniform(0, size_of_bucket-1))) for notUsed2 in range(length)]
            
            ## each element of accountCurveGroup is an accountCurveSingle
            bs_list.append(     
                             accountCurveSingle(
                               pd.DataFrame([values_to_sample_from["gross"][xidx] for xidx in sample], index=index_to_use),
                               pd.DataFrame([values_to_sample_from["net"][xidx] for xidx in sample], index=index_to_use),
                               pd.DataFrame([values_to_sample_from["costs"][xidx] for xidx in sample], index=index_to_use)

                             )
                           )
        
        asset_columns=["b%d" % idx for idx in range(no_runs)]
        
        return accountCurveGroup(bs_list, asset_columns)



if __name__ == '__main__':
    import doctest
    doctest.testmod()
