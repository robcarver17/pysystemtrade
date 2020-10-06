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
from systems.forecasting import TradingRule, Rules
from systems.positionsizing import PositionSizing
from systems.system_cache import input, dont_cache, diagnostic, output
from syscore.fileutils import image_process
from systems.provided.futures_chapter15.rules import ewmac_calc_vol, carry2
from systems.provided.moretradingrules.morerules import relative_carry
from copy import copy
import numpy as np
import pandas as pd
import random
import matplotlib.pylab as plt
from syscore.dateutils import ROOT_BDAYS_INYEAR


def simple_breakout(price, lookback=10):
    """
    :param price: The price or other series to use (assumed Tx1)
    :type price: pd.DataFrame

    :param lookback: Lookback in days
    :type lookback: int


    :returns: pd.DataFrame -- unscaled, uncapped forecast

    """

    roll_max = price.rolling(
        lookback, min_periods=int(min(len(price), np.ceil(lookback / 2.0)))
    ).max()
    roll_min = price.rolling(
        lookback, min_periods=int(min(len(price), np.ceil(lookback / 2.0)))
    ).min()

    roll_mean = (roll_max + roll_min) / 2.0

    # gives a nice natural scaling
    output = (price - roll_mean) / (roll_max - roll_min)

    output[abs(output) < 0.4] = 0

    return output


def simple_mav(price, short=10, long=40):
    """
    Simple moving average crossover

    :param price:
    :param short: days for short
    :param long: days for short
    :return: forecast
    """

    short_mav = price.rolling(short, min_periods=1).mean()
    long_mav = price.rolling(long, min_periods=1).mean()

    signal = short_mav - long_mav

    return signal


class Rules_with_binary(Rules):
    def get_raw_forecast(self, instrument_code, rule_variation_name):

        system = self.parent

        self.log.msg(
            "Calculating raw forecast %s for %s"
            % (instrument_code, rule_variation_name),
            instrument_code=instrument_code,
            rule_variation_name=rule_variation_name,
        )

        trading_rule = self.trading_rules()[rule_variation_name]

        result = trading_rule.call(system, instrument_code)
        result.columns = [rule_variation_name]

        binary = result.apply(sign)
        binary_forecast = 10 * binary

        return binary_forecast


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
    new_position = []
    price_list_since_position_held = []

    for iday in range(len(price)):
        current_price = price[iday]

        if current_position == 0.0:
            # no position, check for signal
            original_position_now = position[iday]
            if np.isnan(original_position_now):
                # no signal
                new_position.append(0.0)
                continue
            if original_position_now > 0.0 or original_position_now < 0.0:
                # potentially going long / short
                # check last position to avoid whipsaw
                if previous_position == 0.0 or sign(
                        original_position_now) != sign(previous_position):
                    # okay to do this - we don't want to enter a new position unless sign changed
                    # we set the position at the sized position at moment of
                    # inception
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

        if sign_position == 1:
            # long
            hwm = np.nanmax(price_list_since_position_held)
            threshold = hwm - trailing_factor
            close_trade = current_price < threshold
        else:
            # short
            hwm = np.nanmin(price_list_since_position_held)
            threshold = hwm + trailing_factor
            close_trade = current_price > threshold

        if close_trade:
            previous_position = copy(current_position)
            current_position = 0.0
            # note if we don't close the current position is maintained
            price_list_since_position_held = []

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
            instrument_code=instrument_code,
        )
        """
        We don't allow this to be changed in config
        """
        avg_abs_forecast = system_defaults["average_absolute_forecast"]

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
        raw_position = self.get_subsystem_position_preliminary(instrument_code)

        subsystem_position = stoploss(price, vol, raw_position, stop_fraction)

        return subsystem_position[0]


simple_mav_rules = dict(
    [
        (
            "mac_%d_%d" % (fast_length, fast_length * 4),
            TradingRule(
                dict(
                    function=simple_mav,
                    other_args=dict(long=fast_length * 4, short=fast_length),
                )
            ),
        )
        for fast_length in [2, 4, 8, 16, 32, 64]
    ]
)

simple_mav_rules_ordered_keys = [
    "mac_%d_%d" % (fast_length, fast_length * 4)
    for fast_length in [2, 4, 8, 16, 32, 64]
]
"""
ewmac_rules = dict([("ewmac_%d_%d" % (fast_length, fast_length*4),
    TradingRule(dict(function = ewmac_calc_vol, other_args = dict(Lfast = fast_length, Lslow = fast_length*4))))
    for fast_length in [2, 4, 8, 16, 32, 64]])

ewmac_rules_ordered_keys = ["ewmac_%d_%d" %(fast_length, fast_length*4)
    for fast_length in [2,4,8,16,32,64]]
"""

breakouts = dict(
    [
        ("breakout_%d" %
         (lookback),
            TradingRule(
             dict(
                 function=simple_breakout,
                 other_args=dict(
                     lookback=lookback))),
         ) for lookback in [
            10,
            20,
            40,
            80,
            160,
            320]])

breakouts_ordered_keys = [
    "breakout_%d" % (smooth) for smooth in [10, 20, 40, 80, 160, 320]
]

carry_rules = dict(
    [
        (
            "carry_%d" % (smooth_days),
            TradingRule(
                dict(function=carry2, other_args=dict(smooth_days=smooth_days))
            ),
        )
        for smooth_days in [10, 30, 60, 125]
    ]
)

carry_ordered_keys = [
    "carry_%d" %
    (smooth_days) for smooth_days in [
        10, 30, 60, 125]]

relative_carry_rule = dict(
    relative_carry=TradingRule(
        dict(
            function=relative_carry,
            data=[
                "rawdata.smoothed_carry",
                "rawdata.median_carry_for_asset_class"],
        )))

rel_carry_key = ["relative_carry"]


# returns
def SR_error_bars_from_values(annual_SR, len_data):

    daily_SR = annual_SR / 16

    var_of_SR_estimator_daily = (1 + 0.5 * (daily_SR ** 2)) / len_data
    std_of_SR_estimator_daily = var_of_SR_estimator_daily ** 0.5
    std_of_SR_estimator_annual = std_of_SR_estimator_daily * 16

    error_bar_annual = std_of_SR_estimator_annual * 1.96

    low_SR_estimate = annual_SR - 2 * error_bar_annual
    upper_SR_estimate = annual_SR + 2 * error_bar_annual

    return low_SR_estimate, annual_SR, upper_SR_estimate


def SR_error_bars(account_curve):
    """
    returns 95% min and max values for an account curve

    :param account_curve: something produced by system.accounts
    :return: list of two
    """

    annual_SR = account_curve.sharpe()
    len_data = len(account_curve.index)  # working days

    low_SR_estimate, annual_SR, upper_SR_estimate = SR_error_bars_from_values(
        annual_SR, len_data
    )

    return [low_SR_estimate, annual_SR, upper_SR_estimate]


def get_curvestack_for_rule(system, rulename, curvetype="gross"):
    curves = [
        system.accounts.pandl_for_trading_rule_unweighted(rulename).to_frame("gross")[
            instrument
        ]
        for instrument in system.get_instrument_list()
    ]
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

    annual_SR = daily_mean * 16 / daily_std
    len_data = len(curve_stack.index)  # working days

    low_SR_estimate, annual_SR, upper_SR_estimate = SR_error_bars_from_values(
        annual_SR, len_data
    )

    return [low_SR_estimate, annual_SR, upper_SR_estimate]


def get_SR_bars_for_rule(rulename, system):
    curvestack = get_curvestack_for_rule(system, rulename)
    return SR_error_bars_from_stacked(curvestack)


# number of trades per year
def tradesperyear(x):
    y = x != x.shift(1)
    totaly = y.sum()
    years = len(y) / 250.0

    return totaly / years


# For each rule we want - the gross stacked sharpe ratios, and the turnover
# all_rules = {**simple_mav_rules, **ewmac_rules, **breakouts,
# **carry_rules, **relative_carry_rule}
"""
for (ordered_names, rule_set_name, rule_set) in zip(
        [simple_mav_rules_ordered_keys, ewmac_rules_ordered_keys, breakouts_ordered_keys, rel_carry_key],
        ["simple_mav", "ewmav", "breakout", "relative carry"],
        [simple_mav_rules, ewmac_rules, breakouts, carry_rules, relative_carry_rule]):
"""

for (ordered_names, rule_set_name, rule_set) in zip(
    [breakouts_ordered_keys], ["breakout"], [breakouts]
):

    config = Config(
        dict(
            trading_rules=rule_set,
            stop_fraction=0.5,
            percentage_vol_target=12.0,
            use_instrument_div_mult_estimates=True,
        )
    )
    data = csvFuturesSimData()
    system = System(
        [
            Account(),
            Portfolios(),
            PositionSizeWithStopLoss(),
            FuturesRawData(),
            ForecastCombine(),
            ForecastScaleCap(),
            Rules_with_binary(rule_set),
        ],
        data,
        config,
    )
    system.set_logging_level("on")
    """
    all_average_SRs= [get_SR_bars_for_rule(rulename, system) for rulename in ordered_names]
    SR_by_rule_bars = pd.DataFrame(all_average_SRs, ordered_names, columns=["lower", "mean", "upper"])
    SR_by_rule_bars.transpose().plot(kind="box",rot=90)
    plt.rcParams.update({'font.size': 24})
    plt.gcf().subplots_adjust(bottom=0.35)
    image_process("SR_by_rule_error_bars_%s" % rule_set_name)
    plt.close()
    """

    results = []
    for rule_name in ordered_names:
        # all_positions=[system.rules.get_raw_forecast(instrument, rule_name) for instrument in system.get_instrument_list()]

        all_positions_stacked = pd.concat(all_positions, axis=0)

        results.append((rule_name, tradesperyear(all_positions_stacked)))

    print(results)
    notUsed = input("press return")
    """
    for rule_name in ordered_names:
        this_rule_dict = dict(rule0 = rule_set[rule_name])
        config = Config(dict(trading_rules=this_rule_dict, stop_fraction=.5,
                             percentage_vol_target=12.0,
                             use_instrument_div_mult_estimates=True,
                             ))
        data = csvFuturesSimData()
        system = System([
            Account(), Portfolios(), PositionSizeWithStopLoss(), FuturesRawData(),
            ForecastCombine(), ForecastScaleCap(), Rules_with_binary(this_rule_dict)
        ], data, config)
        system.set_logging_level("on")

        SR_by_instrument_list_bars = [SR_error_bars(system.accounts.pandl_for_subsystem(code).gross) for code in system.get_instrument_list()]
        SR_by_instrument_bars = pd.DataFrame(SR_by_instrument_list_bars, system.get_instrument_list(), columns=["lower", "mean", "upper"])
        SR_by_instrument_bars = SR_by_instrument_bars.sort_values(by="mean")
        SR_by_instrument_bars.transpose().plot(kind="box",rot=90)
        plt.rcParams.update({'font.size': 24})
        plt.gcf().subplots_adjust(bottom=0.2)
        image_process("SR_by_instrument_error_bars_%s" % rule_name)
        plt.close()

    """

all_rules = {**simple_mav_rules, **breakouts, **dict(carry=carry_rules["carry_10"])}
config = Config(
    dict(
        trading_rules=all_rules,
        stop_fraction=0.5,
        percentage_vol_target=12.0,
        use_instrument_div_mult_estimates=True,
    )
)
data = csvFuturesSimData()
system = System(
    [
        Account(),
        Portfolios(),
        PositionSizeWithStopLoss(),
        FuturesRawData(),
        ForecastCombine(),
        ForecastScaleCap(),
        Rules_with_binary(all_rules),
    ],
    data,
    config,
)
system.set_logging_level("on")

system.config.forecast_weight_estimate["ceiling_cost_SR"] = 9999

ordered_rule_names = simple_mav_rules_ordered_keys + \
    breakouts_ordered_keys + ["carry"]

all_average_SRs = [
    get_SR_bars_for_rule(rulename, system) for rulename in ordered_rule_names
]
SR_by_rule_bars = pd.DataFrame(
    all_average_SRs, ordered_rule_names, columns=["lower", "mean", "upper"]
)
SR_by_rule_bars.transpose().plot(kind="box", rot=90)
plt.rcParams.update({"font.size": 24})
plt.gcf().subplots_adjust(bottom=0.35)
image_process("SR_by_rule_error_bars_all_rules_chapter_8")
plt.close()


# Monte carlo adding rules
def results_stack_given_a_rule_subset(all_rule_pandl_frame, rule_name_list):
    subset_frame = all_rule_pandl_frame[rule_name_list]
    mean_results = subset_frame.mean(axis=1)

    return mean_results


all_rule_pandl = system.accounts.pandl_for_all_trading_rules_unweighted()
all_rule_pandl_frame = all_rule_pandl.to_frame()

# Correlations
all_rule_pandl_frame.corr()

rule_length = len(ordered_rule_names)

MAX_PERMS = 100
all_results = []
for rule_count in range(1, rule_length):

    def pick_rules(all_rule_names, rule_count, rule_length):
        # pick with replacement
        possible_indices = [x for x in range(rule_length)]
        pick_indices = [
            possible_indices.pop(int(random.uniform(0, len(possible_indices))))
            for notUsed in range(rule_count)
        ]

        rule_name_list = [all_rule_names[rule_index]
                          for rule_index in pick_indices]

        return rule_name_list

    possible_perms = [
        pick_rules(ordered_rule_names, rule_count, rule_length)
        for notUsed in range(MAX_PERMS)
    ]

    curves = [
        results_stack_given_a_rule_subset(all_rule_pandl_frame, rule_name_list)
        for rule_name_list in possible_perms
    ]
    curve_stack = pd.concat(curves, axis=0)
    sr_bars = SR_error_bars_from_stacked(curve_stack)

    all_results.append(sr_bars)

SR_by_rule_bars = pd.DataFrame(
    all_results,
    list(
        range(
            1,
            rule_length)),
    columns=[
        "lower",
        "mean",
        "upper"])
SR_by_rule_bars.transpose().plot(kind="box", rot=90)
plt.rcParams.update({"font.size": 24})
plt.gcf().subplots_adjust(bottom=0.35)
image_process("SR_by_rule_adding_more_rules")
plt.close()

# plot some crude
price = data.get_raw_price("CRUDE_W")[
    pd.datetime(
        2010, 1, 1): pd.datetime(
            2016, 1, 1)]
price.plot()
plt.rcParams.update({"font.size": 24})
image_process("Crude oil breakout")
plt.close()

lookback = 320

roll_max = price.rolling(
    lookback, min_periods=int(min(len(price), np.ceil(lookback / 2.0)))
).max()
roll_min = price.rolling(
    lookback, min_periods=int(min(len(price), np.ceil(lookback / 2.0)))
).min()

roll_mean = (roll_max + roll_min) / 2.0

stacked_stuff = pd.concat([price, roll_max, roll_min, roll_mean], axis=1)
stacked_stuff.set_axis(["price", "Max", "Min", "Avg"],
                       axis="columns", inplace=True)
stacked_stuff.plot()
plt.rcParams.update({"font.size": 24})
image_process("crude_oil_breakout_values")
plt.close()
