"""

The starter system has the following features:

- single market
- binary forecast from simple MAV
- exit from trailing stop loss
- fixed positions once in trade

"""
import math
import pickle
from itertools import combinations, chain
from systems.defaults import system_defaults
from syscore.genutils import sign
from systems.provided.futures_chapter15.basesystem import *
from sysdata.configdata import Config
from systems.forecasting import TradingRule
from systems.positionsizing import PositionSizing
from systems.system_cache import input, dont_cache, diagnostic, output
from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.fileutils import image_process

from copy import copy
import numpy as np
import pandas as pd
import random
from random import getrandbits
import matplotlib.pylab as plt

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

def stoploss(price, vol, position, annual_stoploss_fraction=0.5):
    """
    Apply trailing stoploss

    :param price:
    :param daily vol: eg system.rawdata.daily_returns_volatility("SP500")
    :param position: Raw position series, without stoploss or entry / exit logic
    :return: New position series
    """
    Xfactor = annual_stoploss_fraction * ROOT_BDAYS_INYEAR

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

        stop_fraction = self.parent.config.stop_fraction
        price = self.parent.rawdata.get_daily_prices(instrument_code)
        vol = self.parent.rawdata.daily_returns_volatility(instrument_code)
        raw_position=self.get_subsystem_position_preliminary(instrument_code)

        subsystem_position = stoploss(price,vol,raw_position,stop_fraction)

        return subsystem_position[0]

def calc_perms(n,r):
    return math.factorial(n)/(math.factorial(r)*math.factorial(n-r))

def SR_error_bars_from_values(annual_SR, len_data):

    daily_SR = annual_SR/16

    var_of_SR_estimator_daily = (1+0.5*(daily_SR**2))/len_data
    std_of_SR_estimator_daily = var_of_SR_estimator_daily**.5
    std_of_SR_estimator_annual = std_of_SR_estimator_daily *16

    error_bar_annual = std_of_SR_estimator_annual*1.96

    low_SR_estimate = annual_SR - 2*error_bar_annual
    upper_SR_estimate = annual_SR+ 2*error_bar_annual

    return low_SR_estimate, annual_SR, upper_SR_estimate


def SR_error_bars(account_curve, shift_value):
    """
    returns 95% min and max values for an account curve

    :param account_curve: something produced by system.accounts
    :return: list of two
    """

    annual_SR = approx_SR(account_curve)
    len_data = len(account_curve) # working days

    low_SR_estimate, annual_SR, upper_SR_estimate = SR_error_bars_from_values(annual_SR, len_data)

    return [low_SR_estimate+shift_value, annual_SR+shift_value, upper_SR_estimate+shift_value]


simple_mav_rule=TradingRule(dict(function = simple_mav, other_args=dict(long=64, short=16)))

data = csvFuturesSimData()

"""
# all instruments, non trading periods
config= Config(dict(trading_rules = dict(simple_mav=simple_mav_rule), stop_fraction = 0.5,
                        percentage_vol_target=12.0,
                    use_instrument_div_mult_estimates=False
                    ))

system = System([
        Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
        ForecastCombine(), ForecastScaleCap(), Rules(simple_mav_rule)
    ], data, config)
system.set_logging_level("on")

def count_zeros(x):
    y = x==0
    return y.sum()/float(len(x))

zero_fracts = [count_zeros(system.positionSize.get_subsystem_position(code)==0) for code in system.get_instrument_list()]

# just two instruments
config= Config(dict(trading_rules = dict(simple_mav=simple_mav_rule), stop_fraction=.5,
                        percentage_vol_target=12.0, instrument_weights = dict(EUROSTX=6.5/12.5, US10 = 6.0/12.5),
                    use_instrument_div_mult_estimates=False
                    ))

system = System([
        Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
        ForecastCombine(), ForecastScaleCap(), Rules(simple_mav_rule)
    ], data, config)
system.set_logging_level("on")

x=system.accounts.portfolio().as_percent()
x[pd.datetime(2013,4,1):].std()

y=system.accounts.portfolio().to_frame()
y[pd.datetime(2013,4,1):].corr()

std_by_instrument_list = [system.accounts.pandl_for_subsystem(code).gross.annual.as_percent().std() for code in system.get_instrument_list()]
"""

## Plot improvement from adding instruments

config= Config(dict(trading_rules = dict(simple_mav=simple_mav_rule), stop_fraction=.5,
                        percentage_vol_target=12.0,
                    use_instrument_div_mult_estimates=True,
                    ))

system = System([
        Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
        ForecastCombine(), ForecastScaleCap(), Rules(simple_mav_rule)
    ], data, config)
system.set_logging_level("on")

# pre-calculate
all_returns = [system.accounts.pandl_for_subsystem(code) for code in system.get_instrument_list()]

all_instrument_codes = copy(system.get_instrument_list()) ## will be overriden
instrument_length = len(all_instrument_codes)

MAX_PERMS = 50

all_counts = [x for x in range(8,38)]

for instrument_count in all_counts:
    results_for_this_count = []

    def pick_markets(all_instrument_codes, instrument_count, instrument_length):

        ## pick with replacement
        possible_indices = [x for x in range(instrument_length)]
        pick_indices = [possible_indices.pop(int(random.uniform(0,len(possible_indices)))) for notUsed in range(instrument_count)]

        instrument_codes = [all_instrument_codes[instrument_index] for instrument_index in pick_indices]

        return tuple(instrument_codes)

    possible_perms = [pick_markets(all_instrument_codes, instrument_count, instrument_length) for notUsed in range(MAX_PERMS)]

    weight = 1.0 / instrument_count

    for which_run, instruments in zip(range(len(possible_perms)), possible_perms):
        print("\n\n\n\n Run %d for count %d \n\n\n\n\n\n" % (which_run, instrument_count))

        system.cache.delete_items_for_stage("accounts", delete_protected=True)
        system.cache.delete_items_for_stage("portfolio", delete_protected=True)
        system.cache.delete_items_for_stage("base_system", delete_protected=True)

        system.config.instrument_weights = dict([(code, weight) for code in instruments])

        returns = list(system.accounts.portfolio().percent().values)

        # we'll measure SR distribution off the joint
        results_for_this_count.append(returns)

    print("Done and saving %d \n\n\n\n\n\n"% instrument_count)
    f = open("/home/rob/test%d.pck" % instrument_count, "wb")
    pickle.dump(results_for_this_count, f)
    f.close()


# now load
all_counts = [1, 2,3,4,5,6,7, 8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33]

all_results = []
for instrument_count in all_counts:
    f = open("/home/rob/test%d.pck" % instrument_count, "rb")
    results_for_this_count  = pickle.load(f)
    f.close()
    all_results.append(results_for_this_count)

def approx_SR(acc_curve_days):
    return np.nanmean(acc_curve_days)*16/np.nanstd(acc_curve_days)

all_SR = [[approx_SR(acc_curve_days) for acc_curve_days in results_for_this_count] for results_for_this_count in all_results]
avg_SR_by_count = [np.mean(SR_this_count) for SR_this_count in all_SR]
shift_factor = 0.24 - avg_SR_by_count[0]

joined_acc_list = [list(chain(*results_for_this_count)) for results_for_this_count in all_results]
all_SR_bounds = [SR_error_bars(joined_acc, shift_factor) for joined_acc in joined_acc_list]

SR_by_rule_bars = pd.DataFrame(all_SR_bounds, all_counts, columns=["lower", "mean", "upper"])
SR_by_rule_bars.transpose().plot(kind="box",rot=90)
plt.rcParams.update({'font.size': 24})
plt.gcf().subplots_adjust(bottom=0.35)
image_process("instrument_diversification_error_bars")
