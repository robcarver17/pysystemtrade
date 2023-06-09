import datetime
from typing import Tuple

import numpy as np
import pandas as pd

from sysobjects.fills import ListOfFills, Fill, fill_list_of_simple_orders, not_filled
from sysobjects.orders import ListOfSimpleOrdersWithDate, SimpleOrderWithDate

from systems.accounts.order_simulator.pandl_order_simulator import (
    PositionsOrdersFills,
)
from systems.accounts.order_simulator.hourly_market_orders import (
    HourlyMarketOrdersSeriesData,
    HourlyOrderSimulatorOfMarketOrders,
    AccountWithOrderSimulatorForHourlyMarketOrders,
)
from systems.system_cache import diagnostic


class HourlyOrderSimulatorOfLimitOrders(HourlyOrderSimulatorOfMarketOrders):
    def _positions_orders_and_fills_from_series_data(self) -> PositionsOrdersFills:

        positions_orders_fills = _generate_positions_orders_and_fills_from_hourly_series_data_using_limit_orders(
            self.series_data
        )

        return positions_orders_fills


## We only use limit orders
def _generate_positions_orders_and_fills_from_hourly_series_data_using_limit_orders(
    series_data: HourlyMarketOrdersSeriesData,
) -> PositionsOrdersFills:

    unrounded_positions = series_data.hourly_unrounded_positions
    hourly_prices = series_data.hourly_price_series

    list_of_positions = []
    list_of_orders = []
    list_of_fills = []

    starting_position = 0  ## doesn't do anything but makes intention clear
    current_position = starting_position

    for idx, current_datetime in enumerate(unrounded_positions.index[:-1]):
        list_of_positions.append(current_position)

        current_optimal_position = unrounded_positions[idx]
        current_price = hourly_prices[idx]
        next_price = hourly_prices[idx + 1]
        next_datetime = unrounded_positions.index[idx + 1]

        order, fill = _generate_limit_order_and_fill_at_idx_point(
            current_position=current_position,
            current_optimal_position=current_optimal_position,
            current_datetime=current_datetime,
            current_price=current_price,
            next_price=next_price,
            next_datetime=next_datetime,
        )
        if not order.is_zero_order:
            list_of_orders.append(order)

        filled_okay = not (fill is not_filled)
        if filled_okay:
            list_of_fills.append(fill)
            current_position = current_position + fill.qty

    ## Because we don't loop at the final point as no fill is possible, we keep our last position
    ## This ensures the list of positions has the same index as the unrounded list
    list_of_positions.append(current_position)

    positions = pd.Series(list_of_positions, unrounded_positions.index)
    list_of_orders = ListOfSimpleOrdersWithDate(list_of_orders)
    list_of_fills = ListOfFills(list_of_fills)

    return PositionsOrdersFills(
        positions=positions, list_of_orders=list_of_orders, list_of_fills=list_of_fills
    )


def _generate_limit_order_and_fill_at_idx_point(
    current_position: int,
    current_optimal_position: int,
    current_datetime: datetime.datetime,
    current_price: float,
    next_datetime: datetime.datetime,
    next_price: float,
) -> Tuple[SimpleOrderWithDate, Fill]:
    if np.isnan(current_optimal_position):
        quantity = 0
    else:
        quantity = round(current_optimal_position) - current_position

    simple_order = SimpleOrderWithDate(
        quantity=quantity, submit_date=current_datetime, limit_price=current_price
    )
    simple_order_as_list = ListOfSimpleOrdersWithDate(
        [simple_order]
    )  ## future proofing for when we have 2 possible orders that can be filled

    fill = fill_list_of_simple_orders(
        simple_order_as_list,
        market_price=next_price,
        fill_datetime=next_datetime,
    )

    return simple_order, fill


class AccountWithOrderSimulatorForLimitOrders(
    AccountWithOrderSimulatorForHourlyMarketOrders
):
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
