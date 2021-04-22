import pandas as pd

from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.objects import arg_not_supplied

from sysquant.estimators.vol import robust_daily_vol_given_price

from systems.system_cache import dont_cache, diagnostic, output
from systems.accounts.account_costs import accountCosts
from systems.accounts.pandl_calculation import pandlCalculationWithSRCosts
from systems.accounts.curves.account_curve import accountCurve

class accountForecast(accountCosts):

    @property
    def name(self):
        return "accounts"

    @diagnostic(not_pickable=True)
    def pandl_for_instrument_forecast(
            self, instrument_code: str,
            rule_variation_name: str,
            delayfill: bool=True
    ) -> accountCurve:
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

        forecast = self.get_capped_forecast(instrument_code,
                                            rule_variation_name)

        price = self.get_raw_price(instrument_code)

        daily_price_volatility = self.get_daily_returns_volatility(
            instrument_code
        )

        # We NEVER use cash costs for forecasts ...
        SR_cost = self.get_SR_cost_for_instrument_forecast(
            instrument_code, rule_variation_name
        )

        target_abs_forecast = self.target_abs_forecast()

        # We use percentage returns (as no 'capital') and don't round
        # positions
        pandl_fcast = pandl_for_instrument_forecast(forecast,
                                  price = price,
                                  daily_price_volatility = daily_returns_volatility,
                                  target_abs_forecast = target_abs_forecast,
                                  SR_cost = SR_cost,
                                  delayfill = delayfill)

        return pandl_fcast




ARBITRARY_FORECAST_CAPITAL = 100
ARBITRARY_FORECAST_ANNUAL_RISK_TARGET = 0.16
ARBITRARY_FORECAST_DAILY_RISK_TARGET = ARBITRARY_FORECAST_ANNUAL_RISK_TARGET / ROOT_BDAYS_INYEAR




def pandl_for_instrument_forecast(forecast: pd.Series,
                                  price: pd.Series,
                                  daily_price_volatility: pd.Series = arg_not_supplied,
                                  target_abs_forecast: float = 10.0,
                                  SR_cost = 0.0,
                                  delayfill = True):

    if daily_price_volatility is arg_not_supplied:
        daily_price_volatility = robust_daily_vol_given_price(price)

    notional_position = _get_notional_position_for_forecast(forecast,
                                                            daily_returns_volatility =daily_price_volatility,
                                                            target_abs_forecast = target_abs_forecast)

    pandl_calculator = pandlCalculationWithSRCosts(price,
                                SR_cost=SR_cost,
                                positions= notional_position,
                            daily_price_volatility = daily_price_volatility,
                 capital = ARBITRARY_FORECAST_CAPITAL,
                delayfill = delayfill)

    account_curve = accountCurve(pandl_calculator)

    return account_curve

def _get_notional_position_for_forecast(forecast: pd.Series,
                                  daily_returns_volatility: pd.Series = arg_not_supplied,
                                        target_abs_forecast: float = 10.0) -> pd.Series:

    normalised_forecast = _get_normalised_forecast(forecast,
                                                   target_abs_forecast = target_abs_forecast)

    aligned_returns_volatility = daily_returns_volatility.reindex(normalised_forecast.index).ffill()
    inverse_vol_scaling = (ARBITRARY_FORECAST_DAILY_RISK_TARGET  / aligned_returns_volatility)

    notional_position = inverse_vol_scaling * normalised_forecast

    return  notional_position

def _get_normalised_forecast(forecast: pd.Series,
                             target_abs_forecast: float = 10.0) -> pd.Series:

    normalised_forecast = forecast / target_abs_forecast

    return normalised_forecast
