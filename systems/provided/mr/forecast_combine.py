import pandas as pd

from syscore.genutils import sign

from systems.system_cache import output, diagnostic
from systems.forecast_combine import ForecastCombine


class MrForecastCombine(ForecastCombine):
    @output()
    def get_combined_forecast(self, instrument_code: str) -> pd.Series:
        ## We don't use buffering, there is no FDM, there is no real combination at all
        conditioning_forecast = self.conditioning_forecast(instrument_code)

        ## this is already scaled and capped
        forecast_before_filter = self.mr_forecast(instrument_code)

        forecast_after_filter = apply_forecast_filter(
            forecast_before_filter, conditioning_forecast
        )
        forecast_after_filter = forecast_after_filter.ffill()

        return forecast_after_filter

    def conditioning_forecast(self, instrument_code) -> pd.Series:
        return self._get_capped_individual_forecast(
            instrument_code=instrument_code,
            rule_variation_name=self.conditioning_rule_name,
        )

    def mr_forecast(self, instrument_code) -> pd.Series:
        return self._get_capped_individual_forecast(
            instrument_code=instrument_code, rule_variation_name=self.mr_rule_name
        )

    @property
    def conditioning_rule_name(self) -> str:
        return self.mr_config["conditioning_rule"]

    @property
    def mr_rule_name(self) -> str:
        return self.mr_config["mr_rule"]

    @property
    def mr_config(self) -> dict:
        return self.config.mr


def apply_forecast_filter(forecast, conditioning_forecast):
    conditioning_forecast = conditioning_forecast.reindex(
        forecast.index, method="ffill"
    )

    new_values = [
        forecast_overlay_for_sign(forecast_value, filter_value)
        for forecast_value, filter_value in zip(
            forecast.values, conditioning_forecast.values
        )
    ]

    return pd.Series(new_values, forecast.index)


def forecast_overlay_for_sign(forecast_value, filter_value):
    if same_sign(forecast_value, filter_value):
        return forecast_value
    else:
        return 0


def same_sign(x, y):
    return sign(x) == sign(y)
