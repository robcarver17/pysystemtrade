import datetime
from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd

from syscore.cache import Cache
from sysobjects.fills import ListOfFills, Fill
from sysobjects.orders import ListOfSimpleOrdersWithDate, SimpleOrderWithDate

from systems.accounts.order_simulator.account_curve_order_simulator import (
    AccountWithOrderSimulator,
)
from systems.accounts.order_simulator.pandl_order_simulator import (
    OrderSimulator,
    PositionsOrdersFills,
)
from systems.system_cache import diagnostic


@dataclass
class HourlyMarketOrdersSeriesData:
    hourly_price_series: pd.Series
    hourly_unrounded_positions: pd.Series


class HourlyOrderSimulatorOfMarketOrders(OrderSimulator):
    def _diagnostic_df(self) -> pd.DataFrame:
        position_series = self.positions()
        position_df = pd.DataFrame(position_series)

        optimal_positions_series = self.optimal_positions_series()
        optimal_position_df = pd.DataFrame(optimal_positions_series)

        list_of_fills = self.list_of_fills()
        fills_df = list_of_fills.as_pd_df()
        list_of_orders = self.list_of_orders()
        orders_df = list_of_orders.as_pd_df()
        df = pd.concat([optimal_position_df, orders_df, fills_df, position_df], axis=1)
        df.columns = [
            "optimal_position",
            "order_qty",
            "limit_price",
            "fill_qty",
            "fill_price",
            "position",
        ]

        return df

    def prices(self) -> pd.Series:
        return self.series_data.hourly_price_series

    def optimal_positions_series(self) -> pd.Series:
        return self.series_data.hourly_unrounded_positions

    def _positions_orders_and_fills_from_series_data(self) -> PositionsOrdersFills:

        positions_orders_fills = _generate_positions_orders_and_fills_from_hourly_series_data_for_market_orders(
            self.series_data
        )

        return positions_orders_fills

    @property
    def series_data(self) -> HourlyMarketOrdersSeriesData:
        return self.cache.get(self._series_data)

    def _series_data(self) -> HourlyMarketOrdersSeriesData:
        series_data = _build_series_data_for_order_simulator(
            system_accounts_stage=self.system_accounts_stage,
            instrument_code=self.instrument_code,
            is_subsystem=self.is_subsystem,
        )
        return series_data


def _build_series_data_for_order_simulator(
    system_accounts_stage,  ## no explicit type would cause circular import
    instrument_code: str,
    is_subsystem: bool = False,
) -> HourlyMarketOrdersSeriesData:

    hourly_price_series = system_accounts_stage.get_hourly_prices(instrument_code)
    if is_subsystem:
        hourly_unrounded_positions = (
            system_accounts_stage.get_unrounded_subsystem_position_for_order_simulator(
                instrument_code
            )
        )
    else:
        hourly_unrounded_positions = (
            system_accounts_stage.get_unrounded_instrument_position_for_order_simulator(
                instrument_code
            )
        )

    series_data = HourlyMarketOrdersSeriesData(
        hourly_price_series=hourly_price_series,
        hourly_unrounded_positions=hourly_unrounded_positions,
    )
    return series_data


def _generate_positions_orders_and_fills_from_hourly_series_data_for_market_orders(
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
        next_price = hourly_prices[idx + 1]
        next_datetime = unrounded_positions.index[idx + 1]

        order, fill = _generate_order_and_fill_at_idx_point(
            current_position=current_position,
            current_optimal_position=current_optimal_position,
            current_datetime=current_datetime,
            next_price=next_price,
            next_datetime=next_datetime,
        )
        if not order.is_zero_order:
            list_of_orders.append(order)
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


def _generate_order_and_fill_at_idx_point(
    current_position: int,
    current_optimal_position: int,
    current_datetime: datetime.datetime,
    next_datetime: datetime.datetime,
    next_price: float,
) -> Tuple[SimpleOrderWithDate, Fill]:
    if np.isnan(current_optimal_position):
        quantity = 0
    else:
        quantity = round(current_optimal_position) - current_position

    simple_order = SimpleOrderWithDate(
        quantity=quantity,
        submit_date=current_datetime,
    )
    fill = Fill(date=next_datetime, price=next_price, qty=simple_order.quantity)

    return simple_order, fill


class AccountWithOrderSimulatorForHourlyMarketOrders(AccountWithOrderSimulator):
    @diagnostic(not_pickable=True)
    def get_order_simulator(
        self, instrument_code, is_subsystem: bool
    ) -> HourlyOrderSimulatorOfMarketOrders:
        order_simulator = HourlyOrderSimulatorOfMarketOrders(
            system_accounts_stage=self,
            instrument_code=instrument_code,
            is_subsystem=is_subsystem,
        )
        return order_simulator

    def get_unrounded_subsystem_position_for_order_simulator(
        self, instrument_code: str
    ) -> pd.Series:
        return self.get_subsystem_position(instrument_code)

    def get_unrounded_instrument_position_for_order_simulator(
        self, instrument_code: str
    ) -> pd.Series:
        return self.get_notional_position(instrument_code)
