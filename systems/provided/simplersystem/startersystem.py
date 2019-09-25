"""

The starter system has the following features:

- single market
- binary forecast from simple MAV
- exit from trailing stop loss
- fixed positions once in trade

"""
from systems.defaults import system_defaults
from syscore.genutils import sign
from systems.provided.futures_chapter15.basesystem import *
from sysdata.configdata import Config
from systems.forecasting import TradingRule
from systems.positionsizing import PositionSizing
from systems.system_cache import input, dont_cache, diagnostic, output
from syscore.fileutils import image_process

from copy import copy
import numpy as np
import pandas as pd
from random import getrandbits
import matplotlib.pylab as plt

def randomrule(price):
    positions=[getrandbits(1) for notUsed in range(len(price.index))]
    positions = pd.Series(positions, index=price.index)
    positions = positions*20
    positions = positions -10

    return positions

def simple_mav(price, short=10, long=40, forecast_fixed=10):
    """
    Simple moving average crossover

    :param price:
    :param short: days for short
    :param long: days for short
    :return: binary time series
    """

    short_mav = price.rolling(short, min_periods=1).mean()
    long_mav = price.rolling(long, min_periods=1).mean()

    signal = short_mav - long_mav

    binary = signal.apply(sign)
    binary_position = forecast_fixed * binary

    return binary_position

def stoploss(price, vol, position, Xfactor=4):
    """
    Apply trailing stoploss

    :param price:
    :param vol: eg system.rawdata.daily_returns_volatility("SP500")
    :param position: Raw position series, without stoploss or entry / exit logic
    :return: New position series
    """

    # assume all lined up
    current_position = 0.0
    previous_position = 0.0
    new_position=[]
    price_list_since_position_held=[]

    for iday in range(len(price)):
        current_price = price[iday]

        if current_position == 0.0:
            # no position, check for signal
            original_position_now = position[iday]
            if np.isnan(original_position_now):
                # no signal
                new_position.append(0.0)
                continue
            if original_position_now>0.0 or original_position_now<0.0:
                # potentially going long / short
                # check last position to avoid whipsaw
                if previous_position ==0.0 or sign(original_position_now)!=sign(previous_position):
                    # okay to do this - we don't want to enter a new position unless sign changed
                    # we set the position at the sized position at moment of inception
                    current_position = original_position_now
                    price_list_since_position_held.append(current_price)
                    new_position.append(current_position)
                    continue
            # if we've made it this far then:
            # no signal
            new_position.append(0.0)
            continue

        # already holding a position
        # calculate HWM
        sign_position = sign(current_position)
        price_list_since_position_held.append(current_price)
        current_vol = vol[iday]
        trailing_factor = current_vol * Xfactor

        if sign_position==1:
            # long
            hwm= np.nanmax(price_list_since_position_held)
            threshold = hwm - trailing_factor
            close_trade = current_price<threshold
        else:
            # short
            hwm = np.nanmin(price_list_since_position_held)
            threshold = hwm + trailing_factor
            close_trade = current_price>threshold

        if close_trade:
            previous_position = copy(current_position)
            current_position=0.0
            # note if we don't close the current position is maintained
            price_list_since_position_held=[]

        new_position.append(current_position)

    new_position = pd.DataFrame(new_position, price.index)

    return new_position

class PositionSizeWithStopLoss(PositionSizing):
    @diagnostic()
    def get_subsystem_position_preliminary(self, instrument_code):
        """
        Get scaled position (assuming for now we trade our entire capital for one instrument)

        """
        self.log.msg(
            "Calculating subsystem position for %s" % instrument_code,
            instrument_code=instrument_code)
        """
        We don't allow this to be changed in config
        """
        avg_abs_forecast = system_defaults['average_absolute_forecast']

        vol_scalar = self.get_volatility_scalar(instrument_code)
        forecast = self.get_combined_forecast(instrument_code)

        vol_scalar = vol_scalar.reindex(forecast.index).ffill()

        subsystem_position = vol_scalar * forecast / avg_abs_forecast

        return subsystem_position

    @output()
    def get_subsystem_position(self, instrument_code):
        """
        Get scaled position (assuming for now we trade our entire capital for one instrument)

        """

        Xfactor = self.parent.config.Xfactor
        price = self.parent.rawdata.get_daily_prices(instrument_code)
        vol = self.parent.rawdata.daily_returns_volatility(instrument_code)
        raw_position=self.get_subsystem_position_preliminary(instrument_code)

        subsystem_position = stoploss(price,vol,raw_position,Xfactor)

        return subsystem_position[0]

# number of trades per year
def tradesperyear(x):
    y= x!=x.shift(1)
    totaly=y.sum()
    years = len(y)/250.0

    return totaly / years


simple_mav_rule=TradingRule(dict(function = simple_mav, other_args=dict(long=40, short=10)))
random_rule = TradingRule(dict(function = randomrule))


# Use a random rule to get number of trades per year for a given 'X'

results=[]
for Xfactor in [16*0.025]:

    #weights = dict(EDOLLAR=1.0)
    config= Config(dict(trading_rules = dict(simple_mav=random_rule), Xfactor=Xfactor,
                        percentage_vol_target=16.0))

    data = csvFuturesSimData()

    system = System([
        Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
        ForecastCombine(), ForecastScaleCap(), Rules(random_rule)
    ], data, config)
    system.set_logging_level("on")
    all_positions=[system.positionSize.get_subsystem_position(instrument) for instrument in system.get_instrument_list()]

    all_positions_stacked = pd.concat(all_positions,axis=0)

    results.append((Xfactor, tradesperyear(all_positions_stacked)))

## now work out underlying forecast turnover

results=[]
for fastmom in [1,2,4,8,16,32,64,128,256]:
    simple_mav_rule = TradingRule(dict(function=simple_mav, other_args=dict(long=4*fastmom, short=fastmom)))

    #weights = dict(EDOLLAR=1.0)
    config= Config(dict(trading_rules = dict(simple_mav=simple_mav_rule), Xfactor=4,
                        percentage_vol_target=16.0))

    data = csvFuturesSimData()

    system = System([
        Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
        ForecastCombine(), ForecastScaleCap(), Rules(simple_mav_rule)
    ], data, config)
    system.set_logging_level("on")
    all_positions=[system.rules.get_raw_forecast(instrument, 'rule0') for instrument in system.get_instrument_list()]

    all_positions_stacked = pd.concat(all_positions,axis=0)

    results.append((fastmom, tradesperyear(all_positions_stacked)))

"""
now run the basic system; 16,64 crossover plus X=8
"""


fastmom=16
simple_mav_rule = TradingRule(dict(function=simple_mav, other_args=dict(long=4 * fastmom, short=fastmom)))

# weights = dict(EDOLLAR=1.0)
config = Config(dict(trading_rules=dict(simple_mav=simple_mav_rule), Xfactor=8,
                     percentage_vol_target=16.0))

data = csvFuturesSimData()

system = System([
    Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules(simple_mav_rule)
], data, config)
system.set_logging_level("on")

all_positions = [system.positionSize.get_subsystem_position(instrument) for instrument in system.get_instrument_list()]

all_positions_stacked = pd.concat(all_positions, axis=0)

trades_each_year_count = tradesperyear(all_positions_stacked)

# returns
def SR_error_bars_from_values(annual_SR, len_data):

    daily_SR = annual_SR/16

    var_of_SR_estimator_daily = (1+0.5*(daily_SR**2))/len_data
    std_of_SR_estimator_daily = var_of_SR_estimator_daily**.5
    std_of_SR_estimator_annual = std_of_SR_estimator_daily *16

    error_bar_annual = std_of_SR_estimator_annual*1.96

    low_SR_estimate = annual_SR - 2*error_bar_annual
    upper_SR_estimate = annual_SR+ 2*error_bar_annual

    return low_SR_estimate, annual_SR, upper_SR_estimate

def SR_error_bars(account_curve):
    """
    returns 95% min and max values for an account curve

    :param account_curve: something produced by system.accounts
    :return: list of two
    """

    annual_SR = account_curve.sharpe()
    len_data = len(account_curve.index) # working days

    low_SR_estimate, annual_SR, upper_SR_estimate = SR_error_bars_from_values(annual_SR, len_data)

    return [low_SR_estimate, annual_SR, upper_SR_estimate]

# no error bars
SR_by_instrument_list = [system.accounts.pandl_for_subsystem(code).gross.sharpe() for code in system.get_instrument_list()]
SR_by_instrument = pd.Series(SR_by_instrument_list, system.get_instrument_list())

SR_by_instrument = SR_by_instrument.sort_values()

SR_by_instrument.plot(kind="bar")
plt.rcParams.update({'font.size': 24})
plt.gcf().subplots_adjust(bottom=0.2)
image_process("SR_by_instrument")

# with error bars

SR_by_instrument_list_bars = [SR_error_bars(system.accounts.pandl_for_subsystem(code).gross) for code in system.get_instrument_list()]
SR_by_instrument_bars = pd.DataFrame(SR_by_instrument_list_bars, system.get_instrument_list(), columns=["lower", "mean", "upper"])
SR_by_instrument_bars = SR_by_instrument_bars.sort_values(by="mean")
SR_by_instrument_bars.transpose().plot(kind="box",rot=90)
plt.rcParams.update({'font.size': 24})
plt.gcf().subplots_adjust(bottom=0.2)
image_process("SR_by_instrument_error_bars")

## Plot costs vs size

filename = "/home/rob/workspace3/pysystemtrade/systems/provided/simplersystem/costsvssize.csv"
costs_vs_size = pd.read_csv(filename)
costs_vs_size['trading_cost'] = costs_vs_size.Execution_cost_vol*trades_each_year_count + costs_vs_size.Holding_cost_vol

product_types = ['Cash CFD', 'Daily spread bet', 'Spot FX', 'Dated CFD', 'Dated spreadbet', 'Future']
marker_types = ["*","o", "s",">", "<", "v"]

ax = None
handlers = []
for product, marker in zip(product_types, marker_types):
    cs_df_this_product=costs_vs_size[costs_vs_size.Product== product]
    if ax is None:
        # first plot
        ax=cs_df_this_product.plot(x="trading_cost", y="Min_size", kind="scatter", logy=True, logx=True, marker=marker)
        handlers.append(ax)
    else:
        newax=cs_df_this_product.plot(x="trading_cost", y="Min_size", kind="scatter", logy=True, logx=True, marker=marker, ax=ax)
        handlers.append(newax)
    print("Product %s cost %.2f min_size %.2f" % (product, cs_df_this_product.trading_cost.median(), cs_df_this_product.Min_size.median()))


plt.legend(product_types)
plt.rcParams.update({'font.size': 24})
plt.xlabel("Trading cost")
plt.ylabel("Minimum capital")
plt.axvline(x=0.20/3.0, linestyle="--")

image_process("Costs_vs_size_all")

# plot crossover example
price = system.rawdata.get_daily_prices("AUD")
price[pd.datetime(2018,1,1):pd.datetime(2018,6,18)].plot(lw=4)
plt.rcParams.update({'font.size': 24})
image_process("AUD_price")


short_mav = price.rolling(16, min_periods=1).mean()
long_mav = price.rolling(64, min_periods=1).mean()


together = pd.concat([price, short_mav, long_mav], axis=1)
together.columns = ["Price", "16 day MA", "64 day MA"]

#together[pd.datetime(2018,9,1):pd.datetime(2018,10,26)].ffill().plot(lw=4, style=["-","--","-."])
together[pd.datetime(2018,6,18):pd.datetime(2018,11,8)].ffill().plot(lw=4, style=["-","--","-."])
frame=plt.gca()
#frame.annotate("Sell", xy=(pd.datetime(2008,6,16), 1075.0),xytext=(pd.datetime(2008,4,1), 800.0), arrowprops=dict(facecolor='black', shrink=0.05))
#frame.annotate("Buy", xy=(pd.datetime(2009,4,3), price[pd.datetime(2009,4,3)]),xytext=(pd.datetime(2009,2,1), 850.0), arrowprops=dict(facecolor='black', shrink=0.05))
plt.rcParams.update({'font.size': 24})
image_process("AUDUSD_trend2")


## Generate profits for a bunch of MAV, stacked average across instruments

trading_rule_dict={}
ordered_names = []
for fastmom in [2,4,8,16,32,64]:
    rulename = "MAV_%d_%d" % (fastmom, fastmom*4)
    ordered_names.append(rulename)
    simple_mav_rule = TradingRule(dict(function=simple_mav, other_args=dict(long=4 * fastmom, short=fastmom)))
    trading_rule_dict[rulename] = simple_mav_rule

config = Config(dict(trading_rules=trading_rule_dict, Xfactor=8,
                     percentage_vol_target=16.0))
data = csvFuturesSimData()

system = System([
    Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules()
], data, config)
system.set_logging_level("on")


def get_curvestack_for_rule(system, rulename, curvetype="gross"):
    curves = [system.accounts.pandl_for_trading_rule_unweighted(rulename).to_frame("gross")[instrument]
              for instrument in system.get_instrument_list()]
    curve_stack = pd.concat(curves, axis=0)

    return curve_stack

def SR_error_bars_from_stacked(curve_stack):
    """
    returns 95% min and max values for an account curve

    :param account_curve: something produced by system.accounts
    :return: list of three
    """
    daily_mean = curve_stack.mean()
    daily_std = curve_stack.std()

    annual_SR = daily_mean*16 / daily_std
    len_data = len(curve_stack.index) # working days

    low_SR_estimate, annual_SR, upper_SR_estimate = SR_error_bars_from_values(annual_SR, len_data)

    return [low_SR_estimate, annual_SR, upper_SR_estimate]

def get_SR_bars_for_rule(rulename, system):
    curvestack  = get_curvestack_for_rule(system, rulename)
    return SR_error_bars_from_stacked(curvestack)

all_average_SRs= [get_SR_bars_for_rule(rulename, system) for rulename in ordered_names]
SR_by_rule_bars = pd.DataFrame(all_average_SRs, ordered_names, columns=["lower", "mean", "upper"])
SR_by_rule_bars.transpose().plot(kind="box",rot=90)
plt.rcParams.update({'font.size': 24})
plt.gcf().subplots_adjust(bottom=0.35)
image_process("SR_by_rule_error_bars")

# average trades per year

# plot prices
for instrument in ["GOLD", "CORN", "EUROSTX", "GBP"]:
    x=data.get_raw_price(instrument)
    #x[pd.datetime(2015, 1, 1):].plot()
    print(instrument)
    print(x.tail(1))
    #plt.rcParams.update({'font.size': 24})
    #image_process("%s_price" % instrument)

    #plt.close()

for instrument in ["GOLD", "CORN", "EUROSTX", "GBP"]:

    price = system.rawdata.get_daily_prices(instrument)
    short_mav = price.rolling(16, min_periods=1).mean()
    long_mav = price.rolling(64, min_periods=1).mean()


    together = pd.concat([price, short_mav, long_mav], axis=1)
    together.columns = ["Price", "16 day MA", "64 day MA"]

    together[pd.datetime(2018,6,1):pd.datetime(2018,11,8)].plot(lw=4, style=["-","--","-."])
    plt.rcParams.update({'font.size': 24})
    image_process("%s_crossover" % instrument)

    plt.close()

# Simulate the four products in the starter system

fastmom=16
simple_mav_rule = TradingRule(dict(function=simple_mav, other_args=dict(long=4 * fastmom, short=fastmom)))

# weights = dict(EDOLLAR=1.0)
config = Config(dict(trading_rules=dict(simple_mav=simple_mav_rule), Xfactor=8,
                     percentage_vol_target=16.0, weights = dict(GOLD=0.25, CORN=.25, EUROSTX=0.25, GBP=0.25)))

data = csvFuturesSimData()

system = System([
    Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules(simple_mav_rule)
], data, config)
system.set_logging_level("on")
