from typing import Callable
from collections import namedtuple
from dataclasses import dataclass

import datetime
import pandas as pd
import numpy as np


from syscore.cache import Cache
from systems.accounts.order_simulator.simple_orders import (
    ListOfSimpleOrdersWithDate,
    SimpleOrderWithDate,
)
from sysobjects.fills import ListOfFills, Fill
from systems.accounts.order_simulator.fills_and_orders import (
    ListOfSimpleOrdersAndResultingFill,
    empty_list_of_orders_with_no_fills,
)


@dataclass
class PositionsOrdersFills:
    positions: pd.Series
    list_of_orders: ListOfSimpleOrdersWithDate
    list_of_fills: ListOfFills


class OrdersSeriesData(object):
    def __init__(self, price_series: pd.Series, unrounded_positions: pd.Series):
        self.price_series = price_series
        self.unrounded_positions = unrounded_positions


@dataclass
class OrderSimulator:
    system_accounts_stage: object  ## no explicit type as would cause circular import
    instrument_code: str
    is_subsystem: bool = False

    def diagnostic_df(self) -> pd.DataFrame:
        return self.cache.get(self._diagnostic_df)

    def _diagnostic_df(self) -> pd.DataFrame:
        other_df = self._other_diagnostics()
        orders_and_fills_df = self._orders_and_fills_df()
        diagnostic_df = pd.concat([other_df, orders_and_fills_df], axis=1)

        return diagnostic_df

    def _other_diagnostics(self) -> pd.DataFrame:
        position_series = self.positions()
        position_df = pd.DataFrame(position_series)

        optimal_positions_series = self.optimal_positions_series()
        optimal_position_df = pd.DataFrame(optimal_positions_series)

        df_positions = pd.concat([optimal_position_df, position_df], axis=1)
        df_positions.columns = [
            "optimal_position",
            "position",
        ]

        return df_positions

    def _orders_and_fills_df(self) -> pd.DataFrame:
        list_of_fills = self.list_of_fills()
        fills_df = list_of_fills.as_pd_df()
        list_of_orders = self.list_of_orders()
        orders_df = list_of_orders.as_pd_df()
        orders_and_fills_df = pd.concat([orders_df, fills_df], axis=1)
        orders_and_fills_df.columns = [
            "order_qty",
            "limit_price",
            "fill_qty",
            "fill_price",
        ]

        return orders_and_fills_df

    def prices(self) -> pd.Series:
        return self.series_data.price_series

    def optimal_positions_series(self) -> pd.Series:
        return self.series_data.unrounded_positions

    def positions(self) -> pd.Series:
        positions_orders_fills = self.positions_orders_and_fills_from_series_data()
        return positions_orders_fills.positions

    def list_of_fills(self) -> ListOfFills:
        positions_orders_fills = self.positions_orders_and_fills_from_series_data()
        return positions_orders_fills.list_of_fills

    def list_of_orders(self) -> ListOfSimpleOrdersWithDate:
        positions_orders_fills = self.positions_orders_and_fills_from_series_data()
        return positions_orders_fills.list_of_orders

    def positions_orders_and_fills_from_series_data(self) -> PositionsOrdersFills:
        ## Because p&l with orders is path dependent, we generate everything together
        return self.cache.get(self._positions_orders_and_fills_from_series_data)

    def _positions_orders_and_fills_from_series_data(self) -> PositionsOrdersFills:
        series_data = self.series_data
        return generate_positions_orders_and_fills_from_series_data(
            series_data=series_data,
            passed_orders_fills_function=self.orders_fills_function,
            passed_idx_data_function=self.idx_data_function,
        )

    @property
    def series_data(self) -> OrdersSeriesData:
        return self.cache.get(self._series_data)

    def _series_data(self) -> OrdersSeriesData:
        series_data = build_daily_series_data_for_order_simulator(
            system_accounts_stage=self.system_accounts_stage,  # ignore type hint
            instrument_code=self.instrument_code,
            is_subsystem=self.is_subsystem,
        )
        return series_data

    @property
    def cache(self) -> Cache:
        return getattr(self, "_cache", Cache(self))

    @property
    def orders_fills_function(self) -> Callable:
        return generate_order_and_fill_at_idx_point_for_market_orders

    @property
    def idx_data_function(self) -> Callable:
        return get_order_sim_daily_data_at_idx_point


def build_daily_series_data_for_order_simulator(
    system_accounts_stage,  ## no explicit type would cause circular import
    instrument_code: str,
    is_subsystem: bool = False,
) -> OrdersSeriesData:
    price_series = system_accounts_stage.get_daily_prices(instrument_code)
    if is_subsystem:
        unrounded_positions = (
            system_accounts_stage.get_unrounded_subsystem_position_for_order_simulator(
                instrument_code
            )
        )
    else:
        unrounded_positions = (
            system_accounts_stage.get_unrounded_instrument_position_for_order_simulator(
                instrument_code
            )
        )

    price_series = price_series.sort_index()
    unrounded_positions = unrounded_positions.sort_index()

    both_index = pd.concat([price_series, unrounded_positions], axis=1).index

    price_series = price_series.reindex(both_index).ffill()
    unrounded_positions = unrounded_positions.reindex(both_index).ffill()

    series_data = OrdersSeriesData(
        price_series=price_series, unrounded_positions=unrounded_positions
    )
    return series_data


def generate_positions_orders_and_fills_from_series_data(
    series_data: OrdersSeriesData,
    passed_idx_data_function: Callable,
    passed_orders_fills_function: Callable,
) -> PositionsOrdersFills:
    master_index = series_data.price_series.index

    list_of_positions = []
    list_of_orders = []
    list_of_fills = []

    starting_position = 0  ## doesn't do anything but makes intention clear
    current_position = starting_position

    for idx, current_datetime in enumerate(master_index[:-1]):
        list_of_positions.append(current_position)
        data_for_idx = passed_idx_data_function(idx, series_data)
        list_of_orders_and_fill = passed_orders_fills_function(
            current_position=current_position,
            current_datetime=current_datetime,
            data_for_idx=data_for_idx,
        )
        orders = list_of_orders_and_fill.list_of_orders
        fill = list_of_orders_and_fill.fill
        if len(orders) > 0:
            list_of_orders = list_of_orders + orders

            if fill.is_unfilled:
                pass
            else:
                list_of_fills.append(fill)
                current_position = current_position + fill.qty

    ## Because we don't loop at the final point as no fill is possible, we keep our last position
    ## This ensures the list of positions has the same index as the unrounded list
    list_of_positions.append(current_position)

    positions = pd.Series(list_of_positions, master_index)
    list_of_orders = ListOfSimpleOrdersWithDate(list_of_orders)
    list_of_fills = ListOfFills(list_of_fills)

    return PositionsOrdersFills(
        positions=positions, list_of_orders=list_of_orders, list_of_fills=list_of_fills
    )


DataAtIDXPoint = namedtuple(
    "DataAtIDXPoint",
    ["current_optimal_position", "current_price", "next_price", "next_datetime"],
)


def get_order_sim_daily_data_at_idx_point(
    idx: int, series_data: OrdersSeriesData
) -> DataAtIDXPoint:
    unrounded_positions = series_data.unrounded_positions
    prices = series_data.price_series

    current_optimal_position = unrounded_positions[idx]
    next_price = prices[idx + 1]
    current_price = prices[idx]
    next_datetime = unrounded_positions.index[idx + 1]

    return DataAtIDXPoint(
        current_optimal_position=current_optimal_position,
        next_datetime=next_datetime,
        next_price=next_price,
        current_price=current_price,
    )


def generate_order_and_fill_at_idx_point_for_market_orders(
    current_position: int,
    current_datetime: datetime.datetime,
    data_for_idx: DataAtIDXPoint,
) -> ListOfSimpleOrdersAndResultingFill:
    current_optimal_position = data_for_idx.current_optimal_position
    next_datetime = data_for_idx.next_datetime
    next_price = data_for_idx.next_price

    if np.isnan(current_optimal_position):
        quantity = 0
    else:
        quantity = round(current_optimal_position) - current_position

    if quantity == 0:
        return empty_list_of_orders_with_no_fills(fill_datetime=next_datetime)

    simple_order = SimpleOrderWithDate(
        quantity=quantity,
        submit_date=current_datetime,
    )
    fill = Fill(
        date=next_datetime,
        price=next_price,
        qty=simple_order.quantity,
        price_requires_slippage_adjustment=True,
    )
    list_of_orders = ListOfSimpleOrdersWithDate([simple_order])

    return ListOfSimpleOrdersAndResultingFill(list_of_orders=list_of_orders, fill=fill)
