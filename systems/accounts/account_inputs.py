from sysobjects.instruments import instrumentCosts

import pandas as pd
from systems.stage import SystemStage
from systems.system_cache import diagnostic


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

        returns_vol = self.parent.rawdata.daily_returns_volatility(
            instrument_code)

        return returns_vol

    def get_daily_percentage_volatility(self, instrument_code: str) -> pd.Series:
        daily_perc_vol = self.parent.rawdata.get_daily_percentage_volatility(instrument_code)

        return daily_perc_vol

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

    def average_forecast(self) -> float:
        return self.config.average_absolute_forecast

    def get_raw_cost_data(self, instrument_code: str)  -> instrumentCosts:
        return self.parent.data.get_raw_cost_data(instrument_code)

    def get_value_of_block_price_move(self, instrument_code: str) -> float:
        return self.parent.data.get_value_of_block_price_move(instrument_code)

    def get_fx_rate(self, instrument_code: str) -> pd.Series:
        return self.parent.positionSize.get_fx_rate(instrument_code)

    def get_subsystem_position(self, instrument_code: str) -> pd.Series:
        return self.parent.positionSize.get_subsystem_position(instrument_code)

    def get_notional_capital(self) -> float:
        """
        Get notional capital from the previous module

        KEY INPUT

        :returns: float

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.get_notional_capital()
        100000.0
        """
        return self.parent.positionSize.get_vol_target_dict()[
            "notional_trading_capital"
        ]

    def get_annual_risk_target(self) -> float:
        """
        Get annual risk target from the previous module

        KEY INPUT

        :returns: float
        """
        return (
            self.parent.positionSize.get_vol_target_dict()[
                "percentage_vol_target"
            ]
            / 100.0
        )

    def get_average_position_for_instrument_at_portfolio_level(self,
                                                               instrument_code: str) -> pd.Series:
        average_position_for_subsystem = self.get_volatility_scalar(instrument_code)
        scaling_factor = self.get_instrument_scaling_factor(instrument_code)
        scaling_factor_aligned = scaling_factor.reindex(average_position_for_subsystem.index, method="ffill")
        average_position = scaling_factor_aligned * average_position_for_subsystem

        return average_position

    def get_volatility_scalar(self, instrument_code: str) -> pd.Series:
        """
        Get the volatility scalar (position with forecast of +10 using all capital)

        KEY INPUT

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        """

        return self.parent.positionSize.get_volatility_scalar(instrument_code)

    def get_notional_position(self, instrument_code: str) -> pd.Series:
        """
        Get the notional position from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        """
        return self.parent.portfolio.get_notional_position(instrument_code)

    @diagnostic()
    def get_instrument_scaling_factor(self, instrument_code: str) -> pd.Series:
        """
        Get instrument weight * IDM

        The number we multiply subsystem by to get position

        Used to calculate SR costs

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        """
        idm = self.get_instrument_diversification_multiplier()
        instr_weights = self.get_instrument_weights()

        inst_weight_this_code = instr_weights[instrument_code]

        multiplier = inst_weight_this_code * idm

        return multiplier

    def get_instrument_diversification_multiplier(self):
        """
        Get instrument div mult

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        """

        return self.parent.portfolio.get_instrument_diversification_multiplier()

    def get_instrument_weights(self):
        """
        Get instrument weights

        KEY INPUT

        :returns: Tx1 pd.DataFrame


        """

        return self.parent.portfolio.get_instrument_weights()


    @property
    def config(self):
        return self.parent.config

