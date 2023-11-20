import datetime
from typing import Tuple, Callable

import numpy as np


from sysobjects.fills import Fill, empty_fill
from systems.accounts.order_simulator.fills_and_orders import (
    fill_list_of_simple_orders,
    empty_list_of_orders_with_no_fills,
    ListOfSimpleOrdersAndResultingFill,
)
from systems.accounts.order_simulator.simple_orders import (
    ListOfSimpleOrdersWithDate,
    SimpleOrderWithDate,
)

from systems.accounts.order_simulator.account_curve_order_simulator import (
    AccountWithOrderSimulator,
)
from systems.accounts.order_simulator.pandl_order_simulator import (
    DataAtIDXPoint,
)
from systems.accounts.order_simulator.hourly_market_orders import (
    HourlyOrderSimulatorOfMarketOrders,
)
from systems.system_cache import diagnostic


class HourlyOrderSimulatorOfLimitOrders(HourlyOrderSimulatorOfMarketOrders):
    @property
    def orders_fills_function(self) -> Callable:
        return generate_order_and_fill_at_idx_point_for_limit_orders


def generate_order_and_fill_at_idx_point_for_limit_orders(
    current_position: int,
    current_datetime: datetime.datetime,
    data_for_idx: DataAtIDXPoint,
) -> Tuple[ListOfSimpleOrdersWithDate, Fill]:
    current_optimal_position = data_for_idx.current_optimal_position
    if np.isnan(current_optimal_position):
        quantity = 0
    else:
        quantity = round(current_optimal_position) - current_position

    if quantity == 0:
        notional_datetime_for_empty_fill = data_for_idx.next_datetime
        return empty_list_of_orders_with_no_fills(
            fill_datetime=notional_datetime_for_empty_fill
        )

    simple_order = SimpleOrderWithDate(
        quantity=quantity,
        submit_date=current_datetime,
        limit_price=data_for_idx.current_price,
    )
    list_of_orders = ListOfSimpleOrdersWithDate([simple_order])
    fill = fill_list_of_simple_orders(
        list_of_orders=list_of_orders,
        market_price=data_for_idx.next_price,
        fill_datetime=data_for_idx.next_datetime,
    )

    return ListOfSimpleOrdersAndResultingFill(list_of_orders=list_of_orders, fill=fill)


class AccountWithOrderSimulatorForLimitOrders(AccountWithOrderSimulator):
    @diagnostic(not_pickable=True)
    def get_order_simulator(
        self, instrument_code, is_subsystem: bool
    ) -> HourlyOrderSimulatorOfLimitOrders:
        order_simulator = HourlyOrderSimulatorOfLimitOrders(
            system_accounts_stage=self,
            instrument_code=instrument_code,
            is_subsystem=is_subsystem,
        )
        return order_simulator
