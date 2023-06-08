import pandas as pd
def mr_rule(hourly_price: pd.Series,
            daily_price: pd.Series,
            daily_vol: pd.Series,
            mr_span_days: int = 5) -> pd.Series:
    equilibrium = daily_price.ewm(span=mr_span_days).mean()
    daily_vol_hourly = daily_vol.reindex(hourly_price.index, method = "ffill")
    equilibrium = equilibrium.reindex(hourly_price.index, method = "ffill")

    forecast_before_filter = (equilibrium - hourly_price)/ daily_vol_hourly

    return forecast_before_filter