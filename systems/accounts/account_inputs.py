
import pandas as pd
from systems.stage import SystemStage
from systems.system_cache import diagnostic

from sysquant.estimators.vol import robust_vol_calc

class accountInputs(SystemStage):
    def get_raw_price(self, instrument_code: str) -> pd.Series:
        return self.parent.data.get_raw_price(instrument_code)

    def get_daily_price(self, instrument_code: str) -> pd.Series:
        return self.parent.data.daily_prices(instrument_code)

    def get_capped_forecast(self, instrument_code: str,
                            rule_variation_name: str) -> pd.Series:
        return self.parent.forecastScaleCap.get_capped_forecast(
            instrument_code, rule_variation_name
        )

    @diagnostic()
    def get_daily_returns_volatility(self, instrument_code: str) -> pd.Series:

        system = self.parent
        if hasattr(system, "rawdata"):
            returns_vol = system.rawdata.daily_returns_volatility(
                instrument_code)
        else:
            price = self.get_daily_price(instrument_code)
            returns_vol = robust_vol_calc(price.diff())

        return returns_vol


    @input
    def has_same_rules_as_code(self, instrument_code):
        """
        Return instruments with same trading rules as this instrument

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: list of str

        """
        return self.parent.combForecast.has_same_rules_as_code(instrument_code)

    def target_abs_forecast(self) -> float:
        return self.parent.forecastScaleCap.target_abs_forecast()