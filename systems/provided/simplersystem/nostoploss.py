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

def apply_fixed_position(position):
    """
    Turn a variable position into one that is held constant regardless of changes in volatility

    :param position: Raw position series, without stoploss or entry / exit logic
    :return: New position series
    """

    # assume all lined up
    current_position = 0.0
    new_position=[]

    for iday in range(len(position)):
        original_position_now = position[iday]

        if current_position == 0.0:
            # no position, check for signal
            if np.isnan(original_position_now):
                # no signal
                new_position.append(0.0)
                continue
            if original_position_now>0.0 or original_position_now<0.0:
                # go long or short
                current_position = original_position_now
                new_position.append(current_position)
                continue

        if sign(current_position)!=sign(original_position_now):
            # changed sign
            current_position = original_position_now
            new_position.append(current_position)
            continue

        # already holding a position of same sign
        new_position.append(current_position)

    new_position = pd.DataFrame(new_position, position.index)

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


class PositionSizeWithConstantPosition(PositionSizeWithStopLoss):

    @output()
    def get_subsystem_position(self, instrument_code):
        """
        Get scaled position (assuming for now we trade our entire capital for one instrument)

        """
        raw_position=self.get_subsystem_position_preliminary(instrument_code)

        subsystem_position = apply_fixed_position(raw_position)

        return subsystem_position[0]



# number of trades per year
def tradesperyear(x):
    y= x!=x.shift(1)
    totaly=y.sum()
    years = len(y)/250.0

    return totaly / years

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




simple_mav_rule=TradingRule(dict(function = simple_mav, other_args=dict(long=64, short=16)))



"""
now run the basic system; 16,64 crossover plus X=8
"""



# weights = dict(EDOLLAR=1.0)
config = Config(dict(trading_rules=dict(simple_mav=simple_mav_rule), Xfactor=8,
                     percentage_vol_target=16.0))

data = csvFuturesSimData()

system = System([
    Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules(simple_mav_rule)
], data, config)
system.set_logging_level("on")

system_no_stop = System([
    Account(), Portfolios(), PositionSizeWithConstantPosition(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules(simple_mav_rule)
], data, config)
system.set_logging_level("on")


with_stop_loss = system.accounts.portfolio()
without_stop_loss = system_no_stop.accounts.portfolio()


# with error bars

SR_by_system_bars = [SR_error_bars(curve.gross) for curve in [with_stop_loss, without_stop_loss]]
SR_by_system_bars = pd.DataFrame(SR_by_system_bars, ["With stop loss", "Continous trading"], columns=["lower", "mean", "upper"])
SR_by_system_bars.transpose().plot(kind="box",rot=90)
plt.rcParams.update({'font.size': 24})
plt.gcf().subplots_adjust(bottom=0.2)
image_process("SR_with_without_stoploss_bars")


## Generate profits for a bunch of MAV, stacked average across instruments

trading_rule_dict={}
ordered_names = []
for fastmom in [2,4,8,16,32,64]:
    rulename = "MAV_%d_%d" % (fastmom, fastmom*4)
    ordered_names.append(rulename)
    simple_mav_rule = TradingRule(dict(function=simple_mav, other_args=dict(long=4 * fastmom, short=fastmom)))
    trading_rule_dict[rulename] = simple_mav_rule



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

def get_curvestack_for_rule(system):
    curves = [system.accounts.pandl_for_subsystem(instrument).gross
              for instrument in system.get_instrument_list()]
    curve_stack = pd.concat(curves, axis=0)

    return curve_stack

def get_x_for_rulename(rulename):
    dict_frac = dict(MAV_2_8 = 0.1, MAV_4_16 = 0.2, MAV_8_32 = 0.4, MAV_16_64 = 0.5, MAV_32_128 = 0.8, MAV_64_256 = 1.4)
    frac = dict_frac[rulename]
    return frac * 16

def get_SR_bars_for_rule(rulename, trading_rule_dict, pos_sizing_class):
    config = Config(dict(trading_rules=trading_rule_dict, Xfactor=get_x_for_rulename(rulename),
                         percentage_vol_target=16.0))
    data = csvFuturesSimData()
    config.forecast_weights = dict([(rulename, 1.0) for notUsed in [1]])

    system = System([
        Account(), Portfolios(), pos_sizing_class(), FuturesRawData(),
        ForecastCombine(), ForecastScaleCap(), Rules()
    ], data, config)
    system.set_logging_level("on")

    curve = get_curvestack_for_rule(system)

    return SR_error_bars_from_stacked(curve)


all_average_SRs= [get_SR_bars_for_rule(rulename, trading_rule_dict, PositionSizeWithStopLoss) for rulename in ordered_names]
all_average_SRs_no_stops= [get_SR_bars_for_rule(rulename, trading_rule_dict, PositionSizeWithConstantPosition) for rulename in ordered_names]

ordered_names_NS = ["%s NS" % name for name in ordered_names]

SR_by_rule_bars = pd.DataFrame(all_average_SRs, ordered_names, columns=["lower", "mean", "upper"])
SR_by_rule_bars_NS = pd.DataFrame(all_average_SRs_no_stops, ordered_names_NS, columns=["lower", "mean", "upper"])

all_SR = pd.concat([SR_by_rule_bars, SR_by_rule_bars_NS])

joint_order = [[x,y] for x,y in zip(ordered_names[1:4], ordered_names_NS[1:4])]
joint_order = sum(joint_order, [])

all_SR = all_SR.loc[joint_order, :]
all_SR = all_SR-0.16

all_SR.transpose().plot(kind="box",rot=90)
plt.rcParams.update({'font.size': 24})
plt.gcf().subplots_adjust(bottom=0.35)
image_process("SR_across_rules_stop_or_not")


