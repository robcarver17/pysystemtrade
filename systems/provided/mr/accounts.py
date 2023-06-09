import pandas as pd

from systems.system_cache import dont_cache, diagnostic, input
from systems.accounts.curves.account_curve import accountCurve
from systems.accounts.account_curve_order_simulator import AccountWithOrderSimulator

from systems.provided.mr.forecast_combine import MrForecastCombine
from systems.provided.mr.rawdata import MrRawData
from systems.provided.mr.mr_pandl_order_simulator import MROrderSimulator


class MrAccount(AccountWithOrderSimulator):
    @diagnostic(not_pickable=True)
    def get_order_simulator(self, instrument_code, subsystem: bool) -> MROrderSimulator:
        return MROrderSimulator(
            system_accounts_stage=self,
            instrument_code=instrument_code,
            subsystem=subsystem,
        )

    ### The following is required to access information to do the MR positions
    @input
    def daily_equilibrium_price(self, instrument_code: str) -> pd.Series:
        return self.raw_data_stage.daily_equilibrium_price(instrument_code)

    @input
    def conditioning_forecast(self, instrument_code: str) -> pd.Series:
        return self.comb_forecast_stage.conditioning_forecast(instrument_code)

    @property
    def comb_forecast_stage(self) -> MrForecastCombine:
        return self.parent.combForecast

    @property
    def raw_data_stage(self) -> MrRawData:
        return self.parent.rawdata
