import pandas as pd

from syscore.dateutils import ROOT_BDAYS_INYEAR

from systems.system_cache import dont_cache, diagnostic, output
from systems.accounts.account_costs import accountCosts

ARBITRARY_FORECAST_CAPITAL = 100
ARBITRARY_FORECAST_ANNUAL_RISK_TARGET = 0.16
ARBITRARY_FORECAST_DAILY_RISK_TARGET = ARBITRARY_FORECAST_ANNUAL_RISK_TARGET / ROOT_BDAYS_INYEAR

class accountForecast(accountCosts):

    @property
    def name(self):
        return "accounts"

    @diagnostic(not_pickable=True)
    def pandl_for_instrument_forecast(
            self, instrument_code: str,
            rule_variation_name: str,
            delayfill: bool=True
    ):
        """
        Get the p&l for one instrument and forecast; as % of arbitrary capital

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurve

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.pandl_for_instrument_forecast("EDOLLAR", "ewmac8").ann_std()
        0.20270495775586916

        """

        self.log.msg(
            "Calculating pandl for instrument forecast for %s %s"
            % (instrument_code, rule_variation_name),
            instrument_code=instrument_code,
            rule_variation_name=rule_variation_name,
            )

        position = self._get_notional_position_for_forecast(instrument_code,
                                                           rule_variation_name)

        price = self.get_raw_price(instrument_code)

        # We NEVER use cash costs for forecasts ...
        SR_cost = self.get_SR_cost_for_instrument_forecast(
            instrument_code, rule_variation_name
        )

        # We use percentage returns (as no 'capital') and don't round
        # positions
        pandl_fcast = 0

        return pandl_fcast

    ## NEED QUICK AND DIRTY FOR FORECASTS
    def _get_notional_position_for_forecast(self,instrument_code: str,
            rule_variation_name: str) -> pd.Series:

        normalised_forecast = self._get_normalised_forecast(instrument_code,
                                                            rule_variation_name)
        daily_returns_volatility = self.get_daily_returns_volatility(
            instrument_code
        )

        aligned_returns_volatility = daily_returns_volatility.reindex(normalised_forecast.index).ffill()
        inverse_vol_scaling = (ARBITRARY_FORECAST_DAILY_RISK_TARGET  / aligned_returns_volatility)

        notional_position = inverse_vol_scaling * normalised_forecast

        return  notional_position

    @diagnostic()
    def _get_normalised_forecast(self,instrument_code: str,
            rule_variation_name: str) -> pd.Series:

        forecast = self.get_capped_forecast(instrument_code,
                                            rule_variation_name)

        target_abs_forecast = self.target_abs_forecast()

        normalised_forecast = forecast / target_abs_forecast

        return normalised_forecast