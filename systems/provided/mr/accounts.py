import pandas as pd

from systems.system_cache import diagnostic, input
from systems.accounts.order_simulator.account_curve_order_simulator import (
    AccountWithOrderSimulator,
)

from systems.provided.mr.forecast_combine import MrForecastCombine
from systems.provided.attenuate_vol.vol_attenuation_forecast_scale_cap import (
    volAttenForecastScaleCap,
)
from systems.provided.mr.rawdata import MrRawData
from systems.provided.mr.mr_pandl_order_simulator import MROrderSimulator


class MrAccount(AccountWithOrderSimulator):
    @diagnostic(not_pickable=True)
    def get_order_simulator(
        self, instrument_code, is_subsystem: bool
    ) -> MROrderSimulator:
        return MROrderSimulator(
            system_accounts_stage=self,
            instrument_code=instrument_code,
            is_subsystem=is_subsystem,
        )

    ### The following is required to access information to do the MR positions
    @input
    def daily_equilibrium_price(self, instrument_code: str) -> pd.Series:
        return self.raw_data_stage.daily_equilibrium_price(instrument_code)

    @input
    def conditioning_forecast(self, instrument_code: str) -> pd.Series:
        return self.comb_forecast_stage.conditioning_forecast(instrument_code)

    @input
    def forecast_attenuation(self, instrument_code: str) -> pd.Series:
        mr_rule = self.comb_forecast_stage.mr_rule_name
        return self.forecast_scale_stage.get_attenuation_for_rule_and_instrument_indexed_to_forecast(
            instrument_code=instrument_code, rule_variation_name=mr_rule
        )

    @input
    def forecast_scalar(self, instrument_code: str) -> pd.Series:
        mr_rule = self.comb_forecast_stage.mr_rule_name
        return self.forecast_scale_stage.get_forecast_scalar(
            instrument_code=instrument_code, rule_variation_name=mr_rule
        )

    @property
    def forecast_scale_stage(self) -> volAttenForecastScaleCap:
        return self.parent.forecastScaleCap

    @property
    def comb_forecast_stage(self) -> MrForecastCombine:
        return self.parent.combForecast

    @property
    def raw_data_stage(self) -> MrRawData:
        return self.parent.rawdata
