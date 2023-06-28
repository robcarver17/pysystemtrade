from typing import Callable

import pandas as pd


from systems.accounts.order_simulator.hourly_limit_orders import (
    HourlyOrderSimulatorOfLimitOrders,
)

from systems.provided.mr.create_orders import generate_mr_orders_and_fill_at_idx_point
from systems.provided.mr.data_and_constants import MROrderSeriesData, MRDataAtIDXPoint


class MROrderSimulator(HourlyOrderSimulatorOfLimitOrders):
    system_accounts_stage: object  ## no type avoid circular import
    instrument_code: str
    is_subsystem: bool = False

    def _diagnostic_df(self) -> pd.DataFrame:
        raise NotImplemented()

    def _series_data(self) -> MROrderSeriesData:
        series_data = build_mr_series_data(
            system_accounts_stage=self.system_accounts_stage,
            instrument_code=self.instrument_code,
            is_subsystem=self.is_subsystem,
        )
        return series_data

    @property
    def idx_data_function(self) -> Callable:
        return get_mr_sim_hourly_data_at_idx_point

    @property
    def orders_fills_function(self) -> Callable:
        return generate_mr_orders_and_fill_at_idx_point


def build_mr_series_data(
    system_accounts_stage,  ## no type hint avoid circular import
    instrument_code: str,
    is_subsystem: bool = False,
) -> MROrderSeriesData:

    hourly_price_series = system_accounts_stage.get_hourly_prices(instrument_code)

    daily_equilibrium = system_accounts_stage.daily_equilibrium_price(instrument_code)
    equilibrium_hourly_price_series = daily_equilibrium.reindex(
        hourly_price_series.index, method="ffill"
    )

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
        hourly_price_series.index, method="ffill"
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

    forecast_attenuation = system_accounts_stage.forecast_attenuation(instrument_code)
    forecast_attenuation_series = forecast_attenuation.reindex(
        hourly_price_series.index, method="ffill"
    )

    forecast_scalar = system_accounts_stage.forecast_scalar(instrument_code)
    forecast_scalar_series = forecast_scalar.reindex(
        hourly_price_series.index, method="ffill"
    )

    avg_abs_forecast = system_accounts_stage.average_forecast()
    abs_forecast_cap = system_accounts_stage.forecast_cap()

    return MROrderSeriesData(
        equilibrium_hourly_price_series=equilibrium_hourly_price_series,
        average_position_series=average_position_series,
        price_series=hourly_price_series,
        hourly_vol_series=hourly_vol_series,
        conditioning_forecast_series=conditioning_forecast_series,
        avg_abs_forecast=avg_abs_forecast,
        abs_forecast_cap=abs_forecast_cap,
        forecast_attenuation_series=forecast_attenuation_series,
        forecast_scalar_series=forecast_scalar_series,
    )


def get_mr_sim_hourly_data_at_idx_point(
    idx: int, series_data: MROrderSeriesData
) -> MRDataAtIDXPoint:
    prices = series_data.price_series

    current_hourly_price = prices[idx]
    next_hourly_price = prices[idx + 1]

    average_position = series_data.average_position_series[idx]
    equilibrium_price = series_data.equilibrium_hourly_price_series[idx]
    conditioning_forecast = series_data.conditioning_forecast_series[idx]
    forecast_attenuation = series_data.forecast_attenuation_series[idx]
    hourly_vol = series_data.hourly_vol_series[idx]
    forecast_scalar = series_data.forecast_scalar_series[idx]

    next_datetime = prices.index[idx + 1]

    abs_forecast_cap = series_data.abs_forecast_cap
    avg_abs_forecast = series_data.avg_abs_forecast

    return MRDataAtIDXPoint(
        next_hourly_price=next_hourly_price,
        current_hourly_price=current_hourly_price,
        conditioning_forecast=conditioning_forecast,
        forecast_attenuation=forecast_attenuation,
        average_position=average_position,
        equilibrium_price=equilibrium_price,
        abs_forecast_cap=abs_forecast_cap,
        avg_abs_forecast=avg_abs_forecast,
        next_datetime=next_datetime,
        hourly_vol=hourly_vol,
        forecast_scalar=forecast_scalar,
    )
