import pandas as pd

from systems.provided.mr.data_and_constants import MRDataAtIDXPoint

### This rule produces a nominal forecast, but this isn't actually used by the accounting code
###    that generates the orders and fills, and would do the same in production
### Only useful for a quick and dirty view of how the forecast does without limit orders


def mr_rule(
    hourly_price: pd.Series,
    daily_vol: pd.Series,
    daily_equilibrium: pd.Series,
) -> pd.Series:
    daily_vol_indexed_hourly = daily_vol.reindex(hourly_price.index, method="ffill")
    hourly_equilibrium = daily_equilibrium.reindex(hourly_price.index, method="ffill")

    forecast_before_filter = (
        hourly_equilibrium - hourly_price
    ) / daily_vol_indexed_hourly

    return forecast_before_filter


#### Following is the 'real' forecasting code


def calculate_capped_scaled_attenuated_forecast(
    data_for_idx: MRDataAtIDXPoint,
) -> float:
    scaled_attenuated_forecast = calculate_scaled_attenuated_forecast(
        data_for_idx=data_for_idx
    )
    capped_scaled_attenuated_forecast = cap_and_floor_forecast(
        scaled_attenuated_forecast=scaled_attenuated_forecast, data_for_idx=data_for_idx
    )

    return capped_scaled_attenuated_forecast


def calculate_scaled_attenuated_forecast(
    data_for_idx: MRDataAtIDXPoint,
) -> float:
    scaled_forecast = calculate_scaled_forecast(data_for_idx)
    forecast_attenuation = data_for_idx.forecast_attenuation

    return scaled_forecast * forecast_attenuation


def calculate_scaled_forecast(
    data_for_idx: MRDataAtIDXPoint,
) -> float:

    forecast_scalar = data_for_idx.forecast_scalar
    raw_forecast = calculate_raw_forecast(data_for_idx)

    return forecast_scalar * raw_forecast


def calculate_raw_forecast(
    data_for_idx: MRDataAtIDXPoint,
) -> float:
    equilibrium_price = data_for_idx.equilibrium_price
    current_hourly_price = data_for_idx.current_hourly_price
    hourly_vol = data_for_idx.hourly_vol

    return (equilibrium_price - current_hourly_price) / hourly_vol


def cap_and_floor_forecast(
    scaled_attenuated_forecast: float, data_for_idx: MRDataAtIDXPoint
) -> float:
    forecast_cap = +data_for_idx.abs_forecast_cap
    forecast_floor = -data_for_idx.abs_forecast_cap
    capped_scaled_attenuated_forecast = min(
        [
            max([scaled_attenuated_forecast, forecast_floor]),
            forecast_cap,
        ]
    )

    return capped_scaled_attenuated_forecast
