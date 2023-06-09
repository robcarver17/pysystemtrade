import pandas as pd


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
