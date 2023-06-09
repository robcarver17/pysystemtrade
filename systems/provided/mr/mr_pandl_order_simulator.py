from typing import Tuple
from dataclasses import dataclass
import pandas as pd

from systems.provided.mr.accounts import MrAccount

from systems.accounts.order_simulator.pandl_order_simulator import OrderSimulator
from sysobjects.orders import ListOfSimpleOrders


@dataclass
class MROrderSeriesData:
    equilibrium_hourly_price_series: pd.Series
    hourly_price_series: pd.Series
    hourly_vol_series: pd.Series
    conditioning_forecast_series: pd.Series
    average_position_series: pd.Series
    avg_abs_forecast: float = 10.0
    abs_forecast_cap: float = 20.0


class MROrderSimulator(OrderSimulator):
    system_accounts_stage: MrAccount
    instrument_code: str
    subsystem: bool = False

    def _positions_orders_and_fills_from_series_data(self):
        mr_order_series_data = build_mr_series_data(
            self.system_accounts_stage,
            instrument_code=self.instrument_code,
            is_subsystem=self.subsystem,
        )
        return generate_positions_orders_and_fills_from_series_data(
            mr_order_series_data=mr_order_series_data
        )


def build_mr_series_data(
    system_accounts_stage: MrAccount,
    instrument_code: str,
    is_subsystem: bool = False,
) -> MROrderSeriesData:

    daily_equilibrium = system_accounts_stage.daily_equilibrium_price(instrument_code)
    equilibrium_hourly_price_series = daily_equilibrium.reindex()
    hourly_price_series = system_accounts_stage.get_hourly_prices(instrument_code)
    daily_vol_series = system_accounts_stage.get_daily_returns_volatility(
        instrument_code
    )
    hourly_vol_series = daily_vol_series.reindex(
        hourly_price_series.index, method="ffill"
    )
    daily_conditioning_forecast_series = system_accounts_stage.conditioning_forecast(
        instrument_code
    )
    conditioning_forecast_series = daily_conditioning_forecast_series.reindex(
        hourly_price_series.index, method="ffiil"
    )
    if is_subsystem:
        daily_average_position_series = (
            system_accounts_stage.get_average_position_at_subsystem_level(
                instrument_code
            )
        )
    else:
        daily_average_position_series = system_accounts_stage.get_average_position_for_instrument_at_portfolio_level(
            instrument_code
        )

    average_position_series = daily_average_position_series.reindex(
        hourly_price_series.index, method="ffill"
    )
    avg_abs_forecast = system_accounts_stage.average_forecast()
    abs_forecast_cap = system_accounts_stage.forecast_cap()

    return MROrderSeriesData(
        equilibrium_hourly_price_series=equilibrium_hourly_price_series,
        average_position_series=average_position_series,
        hourly_price_series=hourly_price_series,
        hourly_vol_series=hourly_vol_series,
        conditioning_forecast_series=conditioning_forecast_series,
        avg_abs_forecast=avg_abs_forecast,
        abs_forecast_cap=abs_forecast_cap,
    )


def generate_positions_orders_and_fills_from_series_data(
    mr_order_series_data: MROrderSeriesData,
    delayfill: bool = True,
) -> Tuple[ListOfSimpleOrders, list, list]:

    current_position = 0
    list_of_orders = []
    list_of_fills = []
    list_of_positions = []
    master_date_index = mr_order_series_data.hourly_price_series.index

    for idx in range(len(master_date_index)):
        ## requires mr_data to be index matched
        (
            new_position,
            orders,
            fill,
        ) = _generate_positions_orders_and_fills_from_series_data_for_idx(
            idx=idx,
            current_position=current_position,
            mr_order_series_data=mr_order_series_data,
            delayfill=delayfill,
        )
        list_of_fills.append(fill)
        list_of_orders.append(orders)
        list_of_positions.append(new_position)

    ## list of orders and fills need to be timestamped
    return list_of_positions, list_of_orders, list_of_fills


def _generate_positions_orders_and_fills_from_series_data_for_idx(
    idx: int,
    current_position: int,
    mr_order_series_data: MROrderSeriesData,
    delayfill: bool = True,
) -> Tuple[int, order, fill]:
    pass
