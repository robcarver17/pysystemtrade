import datetime
from copy import copy
from dataclasses import dataclass
from typing import List, Callable

import numpy as np

from private.projects.MR_2025.configuration import StratParameters, round_to_tick_size
from syscore.constants import arg_not_supplied


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

def get_stop_loss_order_given_current_trade( parameters: StratParameters,
                                      current_trade: CurrentTrade):

    R = current_trade.R
    K_to_L = parameters.stop_gap_ratio
    stop_gap_in_price_units = round_to_tick_size(R*K_to_L, parameters.tick_size)
    min_gap_in_price_units = parameters.min_ticks_bracket_to_stop*parameters.tick_size

    if stop_gap_in_price_units<min_gap_in_price_units:
        print("Stop too close to bracket, moving %d ticks away" % parameters.min_ticks_bracket_to_stop)
        stop_gap_in_price_units = min_gap_in_price_units

    opening_price = current_trade.price_of_last_opening_trade

    if current_trade.position>0:
        limit =  opening_price - stop_gap_in_price_units
    else:
        limit = opening_price + stop_gap_in_price_units

    size = -current_trade.position

    return Order(
                 size=size,
                 stop_loss=True,
                 level=limit)

@dataclass
class FillAndOrder:
    fill: Fill
    order: Order

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


    def remove_filled_order(self, order: Order):
        self.remove(order)




def get_bracket_orders(R, current_price: float, parameters: StratParameters):
    size = parameters.size
    buy_limit = Order(
                      size=size,
                      stop_loss=False,
                      level=buy_bracket_price(R, current_price, parameters))
    sell_limit = Order(
                      size=-size,
                      stop_loss=False,
                      level=sell_bracket_price(R, current_price, parameters))

    return ListOfOrders([buy_limit, sell_limit])

def buy_bracket_price(R, current_price: float, parameters: StratParameters):
    F = parameters.limit_mult_F
    return round_to_tick_size(current_price - F * (R / 2), parameters.tick_size)

def sell_bracket_price(R, current_price: float, parameters: StratParameters):
    F = parameters.limit_mult_F
    return round_to_tick_size(current_price + F*(R/2), parameters.tick_size)


@dataclass
class RunningPandL:
    running_raw_pandl: float = 0
    running_commissions_paid: float =0
    running_cancel_costs: float = 0

    def open_trade(self, size: int, parameters: StratParameters):
        self.running_commissions_paid += -self.actual_costs(parameters=parameters, size=size)

    def close_trade(self, fill: Fill, current_trade: CurrentTrade, parameters: StratParameters):
        assert current_trade.position == - fill.size
        profit_points = current_trade.position * (fill.price - current_trade.price_of_last_opening_trade)
        profit = profit_points * parameters.multiplier_M*parameters.fx
        self.running_raw_pandl += profit
        self.running_commissions_paid += -self.actual_costs(parameters, fill.size)

    def cancel_order(self, order: Order, parameters: StratParameters):
        self.running_cancel_costs+=-self.cancellation_cost(parameters, order.size)

    def net_pandl(self):
        return self.running_raw_pandl+self.running_cancel_costs+self.running_commissions_paid

    def cancellation_cost(self, parameters: StratParameters, size: int):
        return parameters.cancel_cost_ccy_C*abs(size)*parameters.fx

    def actual_costs(self, parameters: StratParameters, size: int):
        return parameters.cost_ccy_C*abs(size)*parameters.fx



@dataclass
class ActionFromState:
    cancel_orders: bool = False
    new_orders: ListOfOrders = arg_not_supplied
    updated_equilibrium_price: float = np.nan
    updated_R: float = np.nan
    is_new_bracket_orders: bool = False
    is_new_stop_loss_order: bool = False
    is_no_action: bool = False


    @classmethod
    def create_no_action(cls):
        return cls(is_no_action=True)

    @classmethod
    def create_cancel_orders(cls):
        return cls(cancel_orders=True)

    @classmethod
    def create_bracket_orders(cls, bracket_orders: ListOfOrders,
                              updated_equilibrium_price: float, updated_R):
        return cls(new_orders=bracket_orders,
                   updated_equilibrium_price=updated_equilibrium_price, updated_R=updated_R,
                   is_new_bracket_orders=True)

    @classmethod
    def create_stop_loss_order(cls, new_order: Order):
        return cls(is_new_stop_loss_order=True, new_orders=ListOfOrders([new_order]))

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

    def update_from_action(self, action: ActionFromState):

        new_state = self.return_copy()
        new_state.time_index = datetime.datetime.now()
        if action.is_no_action:
           return new_state

        elif action.cancel_orders:
            new_state.cancel_all_orders()

        elif action.is_new_bracket_orders:
            new_state.add_list_of_bracket_orders(action.new_orders,
                                                 current_price=action.updated_equilibrium_price,
                                                 R=action.updated_R)
        elif action.is_new_stop_loss_order:
            new_state.add_stop_loss(order=action.new_orders[0])

        else:
            raise Exception("Action uknown")

        return new_state

    def update_given_broker_fill_and_latest_price(self, order: Order, fill: Fill, current_price: float):
        new_state = self.return_copy()
        new_state.time_index = datetime.datetime.now()
        new_state.orders.remove_filled_order(order)
        new_state.current_price = current_price

        if new_state.flat:
            new_state.update_giving_opening_trade(fill)
        else:
            ## closing trade
            new_state.update_given_closing_trade(fill)

        return new_state

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

    def add_list_of_bracket_orders(self, list_of_orders: List[Order], current_price: float, R: float):
        self.orders+=list_of_orders
        self.current_trade.set_equlibrium_price_and_R(price=current_price, R=R)

    def add_stop_loss(self, order: Order):
        self.orders.append(order)

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



def action_given_current_state(current_state: State, R_calculator: Callable, current_price_getter: Callable) -> ActionFromState:

    if current_state.flat_with_no_orders():
        current_R = R_calculator()
        current_price = current_price_getter()
        if np.isnan(current_price) or np.isnan(current_R):
            return ActionFromState.create_no_action()

        bracket_orders = get_bracket_orders(
            R=current_R,
            current_price=current_price,
            parameters=current_state.parameters
        )
        action = ActionFromState.create_bracket_orders(bracket_orders,
                                                       updated_equilibrium_price=current_price,
                                                       updated_R=current_R)


    elif current_state.flat_with_just_bracket_orders():
        action = ActionFromState.create_no_action()

    elif current_state.has_position_with_single_take_profit_order_but_no_stop_loss():
        stop_order =get_stop_loss_order_given_current_trade(parameters=current_state.parameters,
                                                            current_trade=current_state.current_trade)
        action = ActionFromState.create_stop_loss_order(stop_order)

    elif current_state.has_position_with_take_profit_and_stop_loss():
        action = ActionFromState.create_no_action()

    elif current_state.flat_with_only_stop_loss_order():
        action = ActionFromState.create_cancel_orders()

    elif current_state.flat_with_only_take_profit_order():
        action = ActionFromState.create_cancel_orders()

    else:
        raise Exception("State %s not known")

    return action
