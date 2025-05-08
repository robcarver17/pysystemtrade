import random
from copy import copy
from dataclasses import dataclass
from typing import List

import numpy as np
from matplotlib.pyplot import show
import matplotlib.pyplot as plt
import matplotlib
import datetime
from random import gauss

from syscore.constants import arg_not_supplied

matplotlib.use("TkAgg")
matplotlib.rcParams.update({"font.size": 22})

import pandas as pd

## generate a price series

# Arbitrary daily vol
annual_vol_perc = .2
annual_vol_price = 5700*annual_vol_perc
daily_vol_price = annual_vol_price / 16 # can measure directly
SECONDS_PER_UNIT = 10
ten_second_vol = daily_vol_price / (60*60*8/SECONDS_PER_UNIT)**.5 ##assumes no overnight move

one_day = int(60*60*8/SECONDS_PER_UNIT)

def gen_random_price():
    returns = pd.Series([gauss(sigma=ten_second_vol) for __ in range(one_day)], index = pd.date_range(
        start=datetime.datetime(2025,1,1, 8),
        freq="%ds" % SECONDS_PER_UNIT,
        periods=one_day
    ))
    returns[0] = 5700
    price = returns.cumsum()

    return price


def measure_r_at_lookback(h_seconds: int, price: pd.Series):
    return price.rolling(int(h_seconds/SECONDS_PER_UNIT)).max() -price.rolling(int(h_seconds/SECONDS_PER_UNIT)).min()


@dataclass
class Fill:
    size: int
    price: float

    @classmethod
    def empty(cls):
        return cls(0, np.nan)

    def is_empty(self):
        return self.size==0

@dataclass
class StratParameters:
    limit_mult_F: float
    stop_mult_K: float
    cost_ccy_C: float
    cancel_cost_ccy_C: float
    size: int
    multiplier_M: float
    tick_size: float
    slippage_ticks: float = 0.5
    fx: float = 1
    horizon_seconds: int = 300

@dataclass
class CurrentTrade:
    price_of_last_opening_trade: float = np.nan
    R: float = np.nan
    last_equilibrium_price_used: float = np.nan
    position: int = 0

    @classmethod
    def no_trade(cls):
        return cls()

    def set_equlibrium_price_and_R(self, price: float, R: float):
        self.last_equilibrium_price_used = price
        self.R = R

    def opening_trade(self, fill: Fill):
        self.price_of_last_opening_trade = fill.price
        self.position = fill.size

    def closing_trade(self):
        self.position=0
        self.R=np.nan
        self.last_equilibrium_price_used=np.nan
        self.price_of_last_opening_trade=np.nan

@dataclass
class Order:
    stop_loss: bool
    level: float
    size: int

    @property
    def take_profit(self):
        return not self.stop_loss

    def closes_position(self, position):
        return self.size == -position

    def stop_loss_order_given_take_profit(self,  parameters: StratParameters,
                                          current_trade: CurrentTrade):

        assert self.take_profit
        K = parameters.stop_mult_K
        R = current_trade.R
        original_price = current_trade.last_equilibrium_price_used

        if self.size>0:
            limit = original_price + (R/2)*K
        else:
            limit = original_price - (R/2)*K

        limit = round_to_tick_size(limit, parameters.tick_size)

        return Order(
                     size=self.size,
                     stop_loss=True,
                     level=limit)

    def fill_given_price_or_empty(self, price, parameters: StratParameters):
        fill_price = self.filled_at_price(price, parameters)
        if fill_price is None:
            return Fill.empty()

        return Fill(price=fill_price, size=self.size)

    def filled_at_price(self, price, parameters: StratParameters):
        return fill_price_or_none(order=self, price=price, parameters=parameters)

def fill_price_or_none(order: Order, price: float, parameters: StratParameters):
    fill_price= fill_price_if_long(order,price) if order.size>0 else fill_price_if_short(order, price)
    if APPLY_SLIPPAGE:
        fill_price = apply_slippage(fill_price, parameters, order.size, order.take_profit)

    return fill_price

def fill_price_if_long(order: Order, price):
    if order.stop_loss:
        if price > order.level:
            return price if CONSERVATIVE_FILL else order.level
    else:
        if price < order.level:
            return order.level

    return None


def fill_price_if_short(order: Order, price):
    if order.stop_loss:
        if price < order.level:
            return price if CONSERVATIVE_FILL else order.level
    else:
        if price > order.level:
            return order.level

    return None



def apply_slippage(fill_price: float, parameters: StratParameters, size:int, take_profit:bool):
    if fill_price is None:
        return fill_price
    slippage = parameters.slippage_ticks*parameters.tick_size
    if size>0:
        if take_profit:
            if POSITIVE_SLIP_ON_STOPS:
                return fill_price - slippage
            else:
                return fill_price
        else:
            return fill_price+slippage
    else:
        if take_profit:
            if POSITIVE_SLIP_ON_STOPS:
                return fill_price + slippage
            else:
                return fill_price
        else:
            return fill_price-slippage

def round_to_tick_size(raw_price: float, tick_size: float):
    return np.round(raw_price/tick_size,0)*tick_size

class ListOfOrders(List[Order]):
    @classmethod
    def create_empty(cls):
        return cls([])

    def has_no_orders(self):
        return len(self)==0

    def has_bracketed_orders(self):
        if len(self)!=2:
            return False

        return all([order.take_profit for order in self])

    def has_single_order(self):
        return len(self)==1

    def has_single_take_profit_consistent_with_position_order_but_no_stop_loss(self, position:int):
        if not self.has_single_order():
            return False

        single_order = self[0]
        if not single_order.take_profit:
            return False

        return single_order.closes_position(position)

    def has_single_take_profit_order_and_stop_loss_consistent_with_position(self, position:int):
        if not len(self)==2:
            return False

        count_stop_loss = 0
        count_take_profit =0
        for order in self:
            if not order.closes_position(position):
                return False
            if order.stop_loss:
                count_stop_loss+=1
            elif order.take_profit:
                count_take_profit+=1

        return count_take_profit==1 and count_stop_loss==1

    def has_single_take_profit_order_but_no_stop_loss(self):
        if not self.has_single_order():
            return False

        single_order = self[0]
        return single_order.take_profit

    def has_single_stop_loss_but_no_take_profit(self):
        if not self.has_single_order():
            return False

        single_order = self[0]
        return single_order.stop_loss


    def fill_or_empty_given_price(self, price, parameters: StratParameters) -> Fill:
        fills = []
        for order in self:
            fill = order.fill_given_price_or_empty(price, parameters)
            if fill.is_empty():
                continue
            else:
                fills.append(fill)
                self.remove(order)

        if len(fills)==0:
            return Fill.empty()

        if len(fills)>1:
            raise Exception("Only one order can be filled at a time")

        fill = fills[0]

        return fill

    def add_stop_loss(self, current_trade: CurrentTrade, parameters: StratParameters):
        assert self.has_single_order()
        existing_take_profit_order = self[-1]
        new_stop_loss = existing_take_profit_order.stop_loss_order_given_take_profit(
            parameters=parameters,
            current_trade = current_trade
        )
        self.append(new_stop_loss)

    def add_brackets(self, R, current_price: float, parameters: StratParameters):
        F = parameters.limit_mult_F
        size = parameters.size
        buy_limit = Order(
                          size=size,
                          stop_loss=False,
                          level=round_to_tick_size(current_price - F*(R/2), parameters.tick_size))
        sell_limit = Order(
                          size=-size,
                          stop_loss=False,
                          level=round_to_tick_size(current_price + F*(R/2), parameters.tick_size))

        self.append(buy_limit)
        self.append(sell_limit)

@dataclass
class RunningPandL:
    running_raw_pandl: float = 0
    running_commissions_paid: float =0
    running_cancel_costs: float = 0

    def open_trade(self, size: int, parameters: StratParameters):
        self.running_commissions_paid += -abs(size) * parameters.cost_ccy_C

    def close_trade(self, fill: Fill, current_trade: CurrentTrade, parameters: StratParameters):
        assert current_trade.position == - fill.size
        profit = current_trade.position * (fill.price - current_trade.price_of_last_opening_trade) * parameters.multiplier_M
        self.running_raw_pandl += profit
        self.running_commissions_paid += -self.actual_costs(parameters, fill.size)

    def cancel_order(self, order: Order, parameters: StratParameters):
        self.running_cancel_costs+=-self.cancellation_cost(parameters, order.size)

    def net_pandl(self):
        return self.running_raw_pandl+self.running_cancel_costs+self.running_commissions_paid

    def cancellation_cost(self, parameters: StratParameters, size: int):
        if ZERO_COSTS:
            return 0
        else:
            return parameters.cancel_cost_ccy_C*abs(size)

    def actual_costs(self, parameters: StratParameters, size: int):
        if ZERO_COSTS:
            return 0
        else:
            return parameters.cost_ccy_C*abs(size)





@dataclass
class State:
    position: int
    orders: ListOfOrders
    parameters: StratParameters
    pandl: RunningPandL
    current_trade: CurrentTrade
    current_price: float = np.nan
    time_index: datetime.datetime = datetime.datetime.now()

    def return_copy(self):
        return State(
            position=self.position,
            parameters=self.parameters,
            pandl=copy(self.pandl),
            current_trade=copy(self.current_trade),
            time_index=copy(self.time_index),
            current_price=copy(self.current_price),
            orders=copy(self.orders)
        )

    @classmethod
    def start(cls, parameters: StratParameters):
        return cls(0, ListOfOrders.create_empty(), parameters, RunningPandL(),  CurrentTrade.no_trade())

    def update_fills_given_latest_price(self, current_price: float, time_index: datetime.datetime):
        self.time_index = time_index
        self.current_price = current_price

        fill = self.orders.fill_or_empty_given_price(current_price, parameters=self.parameters)
        if fill.is_empty():
            return fill

        if self.flat:
            self.update_giving_opening_trade(fill)
        else:
            ## closing trade
            self.update_given_closing_trade(fill)


    def update_giving_opening_trade(self, fill: Fill):
        ## opening trade
        self.current_trade.opening_trade(fill)
        self.pandl.open_trade(size=fill.size, parameters=self.parameters)
        self.position = self.position + fill.size

    def update_given_closing_trade(self, fill: Fill):
        self.pandl.close_trade(fill=fill, current_trade=self.current_trade, parameters=self.parameters)
        self.position = self.position + fill.size
        self.current_trade.closing_trade()

    def cancel_all_orders(self):
        __ = [self.pandl.cancel_order(order, parameters=self.parameters) for order in self.orders]
        self.orders = ListOfOrders.create_empty()
        self.current_trade.closing_trade() ## should already be done

    def add_brackets(self, R, current_price):
        self.orders.add_brackets(R=R, current_price=current_price, parameters=self.parameters)
        self.current_trade.set_equlibrium_price_and_R(price=current_price, R=R)

    def add_stop_loss(self):
        self.orders.add_stop_loss(
            current_trade=self.current_trade,
            parameters=self.parameters
        )

    def flat_with_no_orders(self):
        return self.orders.has_no_orders() and self.flat

    def flat_with_just_bracket_orders(self):
        return self.flat and self.orders.has_bracketed_orders()

    def has_position_with_single_take_profit_order_but_no_stop_loss(self):
        return self.has_position and self.orders.has_single_take_profit_consistent_with_position_order_but_no_stop_loss(self.position)

    def has_position_with_take_profit_and_stop_loss(self):
        return self.has_position and self.orders.has_single_take_profit_order_and_stop_loss_consistent_with_position(self.position)

    def flat_with_only_take_profit_order(self):
        return self.flat and self.orders.has_single_take_profit_order_but_no_stop_loss()

    def flat_with_only_stop_loss_order(self):
        return self.flat and self.orders.has_single_stop_loss_but_no_take_profit()


    @property
    def flat(self):
        return self.position==0

    @property
    def has_position(self):
        return not self.flat


def fill_given_current_state(current_state: State,  current_price: float, time_index: datetime.datetime) -> State:
    new_state = current_state.return_copy()
    new_state.update_fills_given_latest_price(current_price, time_index=time_index)

    return new_state

def trade_given_current_state(current_state: State, current_R: float,  current_price: float) -> State:
    new_state = current_state.return_copy()
    if new_state.flat_with_no_orders():
        new_state.add_brackets(current_price=current_price, R=current_R)

    elif new_state.flat_with_just_bracket_orders():
        pass

    elif new_state.has_position_with_single_take_profit_order_but_no_stop_loss():
        new_state.add_stop_loss()

    elif new_state.has_position_with_take_profit_and_stop_loss():
        pass

    elif new_state.flat_with_only_stop_loss_order():
        ## cancel orders
        new_state.cancel_all_orders()

    elif new_state.flat_with_only_take_profit_order():
        ## cancel orders
        new_state.cancel_all_orders()

    else:
        raise Exception("State %s not known")

    return new_state



from syscore.interactive.progress_bar import progressBar

def average_R_of_multiple_runs(parameters: StratParameters, monte=100):
    p = progressBar(monte)
    all_results = []
    for _ in range(monte):
        p.iterate()
        all_results.append(get_single_run_average_R(parameters))

    return np.mean(all_results)


def pandl_of_multiple_runs(parameters: StratParameters, monte=100):
    p = progressBar(monte)
    all_results = []
    for _ in range(monte):
        p.iterate()
        all_results.append(get_single_run_of_tested_states(parameters))

    return all_results

def R_of_multiple_runs(parameters: StratParameters, monte=100):
    p = progressBar(monte)
    all_results = []
    for _ in range(monte):
        p.iterate()
        all_results.append(get_single_run_avg_R(parameters))

    return all_results


def get_single_run_of_tested_states(parameters: StratParameters):
    price = gen_random_price()
    all_states = get_list_of_tested_states(parameters=parameters, price=price)
    return all_states[-1].pandl

def get_single_run_avg_R(parameters: StratParameters):
    price = gen_random_price()
    all_states = get_list_of_tested_states(parameters=parameters, price=price)
    R_values= [state.current_trade.R for state in all_states]
    R_values= pd.Series(R_values)
    R_values=R_values.dropna()

    return np.mean(R_values)


def get_single_run_average_R(parameters: StratParameters):
    price = gen_random_price()
    all_states = get_list_of_tested_states(parameters=parameters, price=price)
    R_values = pd.Series([state.current_trade.R for state in all_states])

    return R_values.mean()


def get_list_of_tested_states(parameters: StratParameters, price: pd.Series):
    R_over_time = measure_r_at_lookback(parameters.horizon_seconds, price)
    current_state = State.start(parameters)
    all_states = []

    for time_index in price.index:

        current_price = price[time_index]
        ## First generate fills at this price
        current_state = fill_given_current_state(current_state, current_price=current_price, time_index=time_index)
        all_states.append(current_state)

        current_R = R_over_time[:time_index].iloc[-1]
        if np.isnan(current_R):
            continue
        current_state = trade_given_current_state(current_state=current_state,
                                                  current_R=current_R,
                                                  current_price=current_price)


    return all_states

def plot_list_of_current_states(all_states):
    plot_position_line(all_states)
    plot_order_lines(all_states)
    show(block=True)

def plot_position_line(all_states: List[State]):
    positions = [state.position for state in all_states]
    index = [state.time_index for state in all_states]
    prices = [state.current_price for state in all_states]
    positions = pd.Series(positions,index=index)
    prices = pd.Series(prices, index=index)

    long_positions = prices[positions>0]
    short_positions = prices[positions<0]
    zero_positions = prices[positions==0]

    long_positions.plot(color='green', marker=".", linestyle="none")
    short_positions.plot(color='red', marker=".", linestyle="none")
    zero_positions.plot(color='gray', marker=".", linestyle="none")

def plot_order_lines(all_states: List[State]):
    index = [state.time_index for state in all_states]
    buy_stop_loss = pd.Series([level_of_current_long_stop_loss_order_or_nan(state.orders) for state in all_states], index=index)
    sell_stop_loss = pd.Series([level_of_current_short_stop_loss_order_or_nan(state.orders) for state in all_states], index=index)
    buy_take_profit = pd.Series([level_of_current_long_take_profit_order_or_nan(state.orders) for state in all_states], index=index)
    sell_take_profit = pd.Series([level_of_current_short_take_profit_order_or_nan(state.orders) for state in all_states], index=index)

    buy_stop_loss.plot(color='lime', marker="x", linestyle="none")
    sell_stop_loss.plot(color='lightsalmon', marker="x", linestyle="none")

    buy_take_profit.plot(color='green', marker="o", linestyle="none")
    sell_take_profit.plot(color='red', marker="o", linestyle="none")


def level_of_current_long_take_profit_order_or_nan(list_of_orders: ListOfOrders):
    relevant_orders = [order for order in list_of_orders if order.take_profit and order.size>0]
    if len(relevant_orders)==0:
        return np.nan

    if len(relevant_orders)>1:
        raise Exception(str(relevant_orders))
    order = relevant_orders[0]

    return order.level


def level_of_current_short_take_profit_order_or_nan(list_of_orders: ListOfOrders):
    relevant_orders = [order for order in list_of_orders if order.take_profit and order.size<0]
    if len(relevant_orders) == 0:
        return np.nan
    if len(relevant_orders) > 1:
        raise Exception(str(relevant_orders))
    order = relevant_orders[0]

    return order.level


def level_of_current_long_stop_loss_order_or_nan(list_of_orders: ListOfOrders):
    relevant_orders = [order for order in list_of_orders if order.stop_loss and order.size>0]
    if len(relevant_orders) == 0:
        return np.nan
    if len(relevant_orders) > 1:
        raise Exception(str(relevant_orders))
    order = relevant_orders[0]

    return order.level


def level_of_current_short_stop_loss_order_or_nan(list_of_orders: ListOfOrders):
    relevant_orders = [order for order in list_of_orders if order.stop_loss and order.size<0]
    if len(relevant_orders) == 0:
        return np.nan
    if len(relevant_orders) > 1:
        raise Exception(str(relevant_orders))
    order = relevant_orders[0]

    return order.level

def plot_pandl_line(all_states: List[State]):
    index = [state.time_index for state in all_states]
    pandl= pd.Series([state.pandl.net_pandl() for state in all_states], index=index)
    pandl = 100+pandl
    pandl.plot()

### EXTRAS
# check ratio of R


def plot_net(list_of_runs:List[RunningPandL], normalise_results: bool = False):
    nets = pd.Series([run.net_pandl() for run in list_of_runs])
    avg = nets.mean()
    std = nets.std()
    skew = nets.skew()
    pd.DataFrame(nets).plot.hist(bins=50)
    if normalise_results:
        norm_by = daily_vol_price*parameters.multiplier_M
        plt.title("Avg %.3f Std %.3f SR %.2f Skew %f" % (avg/norm_by, std/norm_by, 16 * avg / std, skew))
    else:
        plt.title("Avg %.1f Std %.1f SR %.2f Skew %f"  % (avg, std, skew, 16*avg/std))

    show(block=True)

def checkRratio_on_random_data():
    things=[]
    for i in range(1000):
        price = gen_random_price()
        R1200_over_time = measure_r_at_lookback(1200, price)
        R300_over_time = measure_r_at_lookback(300, price)
        Ratio = R1200_over_time  / R300_over_time
        things.append(np.mean(Ratio))

    print(np.mean(things))

def analyse_pandl_multiple_runs(list_of_runs, norm_by = arg_not_supplied):
    nets = pd.Series([run.net_pandl() for run in list_of_runs])
    avg = nets.mean()
    std = nets.std()
    skew = nets.skew()
    if norm_by is arg_not_supplied:
        norm_by = daily_vol_price*parameters.multiplier_M

    return avg/norm_by, std/norm_by, 16*avg/std, skew

all_results = dict()

CONSERVATIVE_FILL = False
ZERO_COSTS = False
APPLY_SLIPPAGE = True
POSITIVE_SLIP_ON_STOPS = False

for horizon_seconds in [120,240,360,480,600,900]:
    for stop_mult_K in [.8, .85, .9, 1, 1.1, 12.5]:
        parameters = StratParameters(
         horizon_seconds=horizon_seconds,
            limit_mult_F=.75,
            stop_mult_K=stop_mult_K,
            multiplier_M=5,
            cost_ccy_C=.25,
            cancel_cost_ccy_C=.25,
            size=1,
            tick_size=0.25
        )

        random.seed(0)
        p = pandl_of_multiple_runs(parameters, monte=100)
        results = analyse_pandl_multiple_runs(p, 7.2)

        all_results["H=%d K=%f" % (horizon_seconds, stop_mult_K)] = results
        print(parameters)
        print(results)

#r_values = pd.Series(average_R_of_multiple_runs(parameters)).mean()
#r_values_daily_vol_units = r_values/daily_vol_price

"""
ZC: Zero costs, stop loss filled at limit
CSL: Costs, stop loss filled at limit
CNP: Costs, stop loss filled at next price
CSL: Costs, stop loss filled at limit + slippage. Slippage - means we assume we earn 1/2 a tick on take profit limit orders, and pay 1/2 a tick on stop losses (of which there will be many more with such tight stops). Essentially it's the approximation I use normally when backtesting, and tries to get us closer to a real order book.
CNPS: Costs, stop loss filled at next price + slippage. Slippage - means we assume we earn 1/2 a tick on take profit limit orders, and pay 1/2 a tick on stop losses (of which there will be many more with such tight stops). Essentially it's the approximation I use normally when backtesting, and tries to get us closer to a real order book.
"""

def generate_acr_random_returns():
    returns = []
    for __ in range(one_day):
        rand_element = gauss(sigma=ten_second_vol)
        units_per_minute = int(60/SECONDS_PER_UNIT)
        last_2_mins=-sum(returns[units_per_minute*2:])
        last_4_mins=-sum(returns[units_per_minute*4:])
        last_8_mins=-sum(returns[units_per_minute*8:])
        last_15_mins=-sum(returns[units_per_minute*15:])
        last_30_mins=sum(returns[units_per_minute*30:])

        next_return = rand_element + 0.005*last_2_mins+\
                                    0.005*last_4_mins+\
                                    0.005*last_8_mins+\
                                    0.005*last_15_mins+\
                                    0.01*last_30_mins
        returns.append(next_return)

    returns = pd.Series(returns, index = pd.date_range(
        start=datetime.datetime(2025,1,1, 8),
        freq="%ds" % SECONDS_PER_UNIT,
        periods=one_day
    ))
    returns[0] = 5700
    price = returns.cumsum()

    return price
