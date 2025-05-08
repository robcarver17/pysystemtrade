from copy import copy
from dataclasses import dataclass
from typing import Callable

import numpy as np

from syscore.dateutils import HOURLY_FREQ
from sysobjects.contracts import futuresContract
from sysproduction.data.prices import diagPrices

TIME_BETWEEN_HEARTBEATS=30
SECONDS_PER_UNIT = 1
BARS_REQUIRED_FOR_ESTIMATION = 4
STRATEGY_NAME = "fastMR"
STD_DEV_BUDGET = 150

@dataclass
class StratParameters:
    cost_ccy_C: float
    cancel_cost_ccy_C: float
    multiplier_M: float
    tick_size: float
    fx: float
    slippage_ticks: float
    min_R: float = np.nan
    max_R: float= np.nan
    stoploss_ccy: float= np.nan
    horizon_seconds: int = 600
    stop_mult_K: float = 0.875 ## CHANGE
    min_slippage_units_L_to_K: int = 5 ## COULD CHNAGE
    min_ticks_bracket_to_stop: int = 3
    size: int = 1 # COULD CHANGE
    limit_mult_F: float = 0.75 ## DO NOT CHANGE

    def ratio_of_range_value_to_costs_of_trading(self, R_estimate: float):
        range_value = R_estimate*self.multiplier_M*self.fx
        costs= self.cost_ccy_C*2

        return range_value/costs

    def approx_daily_vol_cash_terms(self, R_estimate: float):
        vol_in_price_terms = self.approx_daily_vol_price_units(R_estimate)

        return vol_in_price_terms*self.multiplier_M*self.size*self.fx

    def approx_daily_vol_price_units(self, R_estimate: float):
        vol_in_R_terms = self.approx_daily_vol_R_terms()
        return vol_in_R_terms*R_estimate

    def approx_daily_vol_R_terms(self):
        vol_in_R_terms = 16*(self.stop_gap_ratio/.05)**.25
        return vol_in_R_terms*self.size

    @property
    def stop_gap_ratio(self):
        stop_gap_ratio = self.stop_mult_K - self.limit_mult_F
        return stop_gap_ratio

def round_to_tick_size(raw_price: float, tick_size: float):
    return np.round(raw_price/tick_size,0)*tick_size


def init_paramaters(parameters: StratParameters) -> StratParameters:

    min_R =estimated_min_R(parameters)
    max_R = estimated_max_R(parameters)
    daily_stop_out = STD_DEV_BUDGET*1.5

    parameters.min_R=min_R
    parameters.max_R = max_R

    parameters.stoploss_ccy = daily_stop_out

    return parameters


def estimated_min_R(parameters:StratParameters):
    slippage_ticks = max([.5,parameters.slippage_ticks])
    min_ticks_in_price_units = parameters.tick_size * parameters.min_slippage_units_L_to_K*slippage_ticks
    stop_gap_ratio = parameters.stop_gap_ratio
    return min_ticks_in_price_units / stop_gap_ratio

def describe_min_R_calculation(parameters:StratParameters):
    slippage_ticks = max([.5,parameters.slippage_ticks])
    print("Min R %f, based on being %d slippage ticks between L and K, L to K is %f, tick size is %f, slippage in ticks is %f" % (parameters.min_R,
                                                                                                parameters.min_slippage_units_L_to_K,
                                                                                                parameters.stop_gap_ratio,
                                                                                                parameters.tick_size,
                                                                                                slippage_ticks))

def estimated_max_R(parameters:StratParameters):
    sqrt_approx_holding_periods_per_day = (60*60*8/parameters.horizon_seconds)**.5
    risk_budget_per_trade = 2*STD_DEV_BUDGET / sqrt_approx_holding_periods_per_day
    gap = parameters.stop_gap_ratio
    value_of_one_price_unit = parameters.multiplier_M*parameters.fx

    return risk_budget_per_trade / (gap*value_of_one_price_unit)



def describe_max_R_calculation(parameters:StratParameters):
    horizons_per_day = (60 * 60 * 8 / parameters.horizon_seconds)
    sqrt_approx_holding_periods_per_day = horizons_per_day ** .5
    risk_budget_per_trade = 2 * STD_DEV_BUDGET / sqrt_approx_holding_periods_per_day


    print("Max R %.4f =B/G. 2xDaily risk budget %f, horizons per day %.0f, budget per trade B=%.2f. Stop loss ratio gap %f, price unit value %f. Gap in price unit values G=%f" % (
        parameters.max_R,
        2*STD_DEV_BUDGET,
        horizons_per_day,
        risk_budget_per_trade,
        parameters.stop_gap_ratio,
        parameters.fx*parameters.multiplier_M,
        parameters.stop_gap_ratio*parameters.multiplier_M*parameters.fx,

    ) )

def loss_per_trade(parameters:StratParameters, current_R: float):
    gap = parameters.stop_gap_ratio
    value_of_one_price_unit = parameters.multiplier_M*parameters.fx

    return value_of_one_price_unit*gap*current_R


def effective_horizon_at_R(current_R: float, R_to_test: float, original_horizon: int):
    H_original = horizon_given_R_daily_vol_units(current_R)
    H_new = horizon_given_R_daily_vol_units(R_to_test)
    ratio = H_new / H_original
    return int(ratio*original_horizon)


def horizon_given_R_daily_vol_units(R_daily_vol_units: float):
    return 60*(R_daily_vol_units/0.065)**(1/.59)


def interactively_modify_parameters(parameters:StratParameters):
    new_parameters = copy(parameters)
    new_parameters.horizon_seconds = get_input_with_default("Horizon, seconds", parameters.horizon_seconds, int)
    new_parameters.stop_mult_K = get_input_with_default("Stop mult K (F is %f)" % parameters.limit_mult_F, parameters.stop_mult_K, float)
    new_parameters.size = get_input_with_default("Size contracts", parameters.size, int)

    if parameters.size==new_parameters.size and parameters.stop_mult_K==new_parameters.stop_mult_K and parameters.horizon_seconds==new_parameters.horizon_seconds:
        ## no need to regen others
        pass
    else:
        new_parameters = init_paramaters(new_parameters)

    new_parameters.min_R = get_input_with_default("Min R ", parameters.min_R, float)
    new_parameters.max_R = get_input_with_default("Max R ", parameters.max_R, float)
    new_parameters.stoploss_ccy = get_input_with_default("Stop loss per day, account currency", parameters.stoploss_ccy, float)

    return new_parameters


def get_input_with_default(label, default, typecaster: Callable):
    ans = input(label+" (return for default %s)" % str(default))
    if len(ans)==0:
        return default
    return typecaster(ans)


def display_diags(starting_R: float, price: float, parameters: StratParameters):
    print("Parameters %s" % str(parameters))
    multiply_to_day = 3600*8/parameters.horizon_seconds
    equivalent_daily_R = starting_R*(multiply_to_day**.5)
    print("Current estimated R %f from daily prices, %f per day, percentage of price %f is %f%%, annualised %f%%" % (
        starting_R, equivalent_daily_R, price, 100*equivalent_daily_R/price, 1600*equivalent_daily_R/price))
    print("")
    describe_max_R_calculation(parameters)
    print("Effective horizon seconds at maximum R %f" % effective_horizon_at_R(starting_R, parameters.max_R, parameters.horizon_seconds))
    describe_min_R_calculation(parameters)
    print("Effective horizon seconds at minimum R %d" % effective_horizon_at_R(starting_R, parameters.min_R, parameters.horizon_seconds))
    if parameters.max_R<parameters.min_R:
        print("**MAX R LESS THAN MIN_R**")
    elif starting_R<parameters.min_R:
        print("Estimated R less than min")
    elif starting_R>parameters.max_R:
        print("Estimated R greater than max")
    print("")

    R_to_use = min([max([starting_R, parameters.min_R]), parameters.max_R])
    print("R to use: %f" % R_to_use)
    print("")
    print("Thereotical max loss per trade %f, with current R to use" % (loss_per_trade(parameters=parameters, current_R=R_to_use)))
    print("Recommended daily stop out %s" % parameters.stoploss_ccy)
    print("Approx expected daily vol, R terms %f" % parameters.approx_daily_vol_R_terms())
    print("Approx expected daily vol, cash terms %f, using R to use; which is %fXstop loss" % (parameters.approx_daily_vol_cash_terms(R_to_use), parameters.approx_daily_vol_cash_terms(R_to_use)/parameters.stoploss_ccy))
    print("")
    print("Ratio of R value to costs %f with R to use" % parameters.ratio_of_range_value_to_costs_of_trading(R_to_use))
    print("Ratio of R value to costs %f with minimum R " % parameters.ratio_of_range_value_to_costs_of_trading(parameters.min_R))

def estimate_R_from_prices(data_prices: diagPrices, horizon: int, futures_contract: futuresContract) -> float:
    prices = data_prices.get_prices_at_frequency_for_contract_object(frequency=HOURLY_FREQ, contract_object=futures_contract)
    hourly_range = prices.HIGH - prices.LOW
    hourly_range[hourly_range==0] = np.nan
    hourly_range=hourly_range.dropna()
    hourly_range = float(hourly_range.rolling(90).mean().values[-1])
    horizon_range = hourly_range*((horizon/3600)**.5)

    return horizon_range

def get_final_price(data_prices: diagPrices, futures_contract: futuresContract) -> float:
    prices = data_prices.get_prices_at_frequency_for_contract_object(frequency=HOURLY_FREQ, contract_object=futures_contract)
    final_price = prices.FINAL.ffill().values[-1]
    return final_price