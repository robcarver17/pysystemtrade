import pandas as pd

from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.constants import arg_not_supplied
from syscore.pandas.pdutils import sum_series
from sysquant.estimators.vol import robust_daily_vol_given_price

from systems.system_cache import diagnostic
from systems.accounts.account_costs import accountCosts
from systems.accounts.pandl_calculators.pandl_SR_cost import pandlCalculationWithSRCosts
from systems.accounts.curves.account_curve import accountCurve


class accountForecast(accountCosts):
    @diagnostic(not_pickable=True)
    def pandl_for_instrument_forecast_weighted_within_trading_rule(
        self, instrument_code: str, rule_variation_name: str, delayfill: bool = True
    ) -> accountCurve:

        pandl_for_instrument_forecast = self.pandl_for_instrument_forecast(
            instrument_code, rule_variation_name, delayfill=delayfill
        )

        weight = (
            self._normalised_weight_for_forecast_and_instrument_within_trading_rule(
                instrument_code, rule_variation_name=rule_variation_name
            )
        )

        weighted_pandl = pandl_for_instrument_forecast.weight(weight)

        return weighted_pandl

    @diagnostic(not_pickable=True)
    def pandl_for_instrument_forecast_weighted(
        self, instrument_code: str, rule_variation_name: str, delayfill: bool = True
    ) -> accountCurve:

        pandl_for_instrument_forecast = self.pandl_for_instrument_forecast(
            instrument_code, rule_variation_name, delayfill=delayfill
        )

        weight = self._normalised_weight_for_forecast_and_instrument(
            instrument_code, rule_variation_name=rule_variation_name
        )

        weighted_pandl = pandl_for_instrument_forecast.weight(weight)

        return weighted_pandl

    @diagnostic()
    def _normalised_weight_for_forecast_and_instrument_within_trading_rule(
        self,
        instrument_code: str,
        rule_variation_name: str,
    ) -> pd.Series:
        weight = self._unnormalised_weight_for_forecast_and_instrument(
            instrument_code=instrument_code, rule_variation_name=rule_variation_name
        )

        total_weight_for_rule = self._total_unnormalised_weight_for_trading_rule(
            rule_variation_name
        )
        total_weight_aligned = total_weight_for_rule.reindex(weight.index).ffill()

        normalised_weight = weight / total_weight_aligned

        return normalised_weight

    @diagnostic()
    def _total_unnormalised_weight_for_trading_rule(
        self, rule_variation_name: str
    ) -> pd.Series:
        list_of_instruments = self.get_instrument_list()

        list_of_weights = [
            self._unnormalised_weight_for_forecast_and_instrument(
                instrument_code, rule_variation_name=rule_variation_name
            )
            for instrument_code in list_of_instruments
        ]

        sum_weights = sum_series(list_of_weights)

        return sum_weights

    @diagnostic()
    def _normalised_weight_for_forecast_and_instrument(
        self, instrument_code: str, rule_variation_name: str
    ) -> pd.Series:

        weight = self._unnormalised_weight_for_forecast_and_instrument(
            instrument_code=instrument_code, rule_variation_name=rule_variation_name
        )
        total_weight = (
            self._total_unnormalised_weight_across_all_instruments_and_forecasts()
        )
        total_weight_aligned = total_weight.reindex(weight.index).ffill()

        normalised_weight = weight / total_weight_aligned

        return normalised_weight

    @diagnostic()
    def _total_unnormalised_weight_across_all_instruments_and_forecasts(
        self,
    ) -> pd.Series:
        list_of_instruments = self.get_instrument_list()
        list_of_weights = [
            self._total_unnormalised_weight_for_instrument(instrument_code)
            for instrument_code in list_of_instruments
        ]

        sum_of_weights = sum_series(list_of_weights)

        return sum_of_weights

    @diagnostic()
    def _total_unnormalised_weight_for_instrument(
        self, instrument_code: str
    ) -> pd.Series:
        list_of_rules = self.list_of_rules_for_code(instrument_code)
        list_of_weights = [
            self._unnormalised_weight_for_forecast_and_instrument(
                instrument_code, rule_variation_name
            )
            for rule_variation_name in list_of_rules
        ]

        sum_of_weights = sum_series(list_of_weights)

        return sum_of_weights

    @diagnostic()
    def _unnormalised_weight_for_forecast_and_instrument(
        self, instrument_code: str, rule_variation_name: str
    ) -> pd.Series:

        idm = self.instrument_diversification_multiplier()
        fdm = self.forecast_diversification_multiplier(instrument_code)
        instrument_weight = self.specific_instrument_weight(instrument_code)
        forecast_weight = self.forecast_weight(
            instrument_code=instrument_code, rule_variation_name=rule_variation_name
        )

        weighting_df = pd.concat([idm, fdm, instrument_weight, forecast_weight], axis=1)
        weighting_df = weighting_df.ffill()
        weighting_df = weighting_df.bfill()
        joint_weight = weighting_df.product(axis=1)

        return joint_weight

    @diagnostic(not_pickable=True)
    def pandl_for_instrument_forecast(
        self, instrument_code: str, rule_variation_name: str, delayfill: bool = True
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

        forecast = self.get_capped_forecast(instrument_code, rule_variation_name)

        price = self.get_raw_price(instrument_code)

        daily_returns_volatility = self.get_daily_returns_volatility(instrument_code)

        # We NEVER use cash costs for forecasts ...
        SR_cost = self.get_SR_cost_for_instrument_forecast(
            instrument_code, rule_variation_name
        )

        target_abs_forecast = self.target_abs_forecast()

        capital = self.get_notional_capital()
        risk_target = self.get_annual_risk_target()
        value_per_point = self.get_value_of_block_price_move(instrument_code)

        fx = self.get_fx_rate(instrument_code)

        pandl_fcast = pandl_for_instrument_forecast(
            forecast,
            price=price,
            capital=capital,
            fx=fx,
            risk_target=risk_target,
            daily_returns_volatility=daily_returns_volatility,
            target_abs_forecast=target_abs_forecast,
            SR_cost=SR_cost,
            delayfill=delayfill,
            value_per_point=value_per_point,
        )

        return pandl_fcast


ARBITRARY_FORECAST_CAPITAL = 100
ARBITRARY_FORECAST_ANNUAL_RISK_TARGET_PERCENTAGE = 0.16


ARBITRARY_VALUE_OF_PRICE_POINT = 1.0


def pandl_for_instrument_forecast(
    forecast: pd.Series,
    price: pd.Series,
    capital: float = ARBITRARY_FORECAST_CAPITAL,
    fx=arg_not_supplied,
    risk_target: float = ARBITRARY_FORECAST_ANNUAL_RISK_TARGET_PERCENTAGE,
    daily_returns_volatility: pd.Series = arg_not_supplied,
    target_abs_forecast: float = 10.0,
    SR_cost=0.0,
    delayfill=True,
    value_per_point=ARBITRARY_VALUE_OF_PRICE_POINT,
) -> accountCurve:

    if daily_returns_volatility is arg_not_supplied:
        daily_returns_volatility = robust_daily_vol_given_price(price)

    normalised_forecast = _get_normalised_forecast(
        forecast, target_abs_forecast=target_abs_forecast
    )

    average_notional_position = _get_average_notional_position(
        daily_returns_volatility,
        risk_target=risk_target,
        value_per_point=value_per_point,
        capital=capital,
    )

    notional_position = _get_notional_position_for_forecast(
        normalised_forecast, average_notional_position=average_notional_position
    )

    pandl_calculator = pandlCalculationWithSRCosts(
        price,
        SR_cost=SR_cost,
        positions=notional_position,
        fx=fx,
        daily_returns_volatility=daily_returns_volatility,
        average_position=average_notional_position,
        capital=capital,
        value_per_point=value_per_point,
        delayfill=delayfill,
    )

    account_curve = accountCurve(pandl_calculator)

    return account_curve


def _get_notional_position_for_forecast(
    normalised_forecast: pd.Series, average_notional_position: pd.Series
) -> pd.Series:

    aligned_average = average_notional_position.reindex(
        normalised_forecast.index, method="ffill"
    )

    return aligned_average * normalised_forecast


def _get_average_notional_position(
    daily_returns_volatility: pd.Series,
    capital: float = ARBITRARY_FORECAST_CAPITAL,
    risk_target: float = ARBITRARY_FORECAST_ANNUAL_RISK_TARGET_PERCENTAGE,
    value_per_point=ARBITRARY_VALUE_OF_PRICE_POINT,
) -> pd.Series:

    daily_risk_target = risk_target / ROOT_BDAYS_INYEAR
    daily_cash_vol_target = capital * daily_risk_target

    instrument_currency_vol = daily_returns_volatility * value_per_point
    average_notional_position = daily_cash_vol_target / instrument_currency_vol

    return average_notional_position


def _get_normalised_forecast(
    forecast: pd.Series, target_abs_forecast: float = 10.0
) -> pd.Series:

    normalised_forecast = forecast / target_abs_forecast

    return normalised_forecast
