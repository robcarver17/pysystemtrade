import pandas as pd

from systems.stage import SystemStage
from systems.system_cache import input, dont_cache, diagnostic, output

from sysquant.estimators.vol import robust_vol_calc
from syscore.algos import apply_buffer
from sysobjects.instruments import instrumentCosts

ARBITRARY_FORECAST_CAPITAL = 100.0


class _AccountInput(SystemStage):
    """
    Partial SystemStage for accounting

    Inherited by class in account.py

    Code split up into this file, and account.py

    Name: accounts
    """


    @input
    def get_capped_forecast(self, instrument_code, rule_variation_name):
        """
        Get the capped forecast from the previous module


        KEY INPUT

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: Tx1 pd.DataFrames

        """
        return self.parent.forecastScaleCap.get_capped_forecast(
            instrument_code, rule_variation_name
        )

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

    @input
    def get_forecast_weights(self, instrument_code):
        """
        Get the capped forecast from the previous module

        KEY INPUT

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: dict of Tx1 pd.DataFrames

        """
        return self.parent.combForecast.get_forecast_weights(instrument_code)

    @input
    def get_instrument_diversification_multiplier(self):
        """
        Get instrument div mult

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        """

        return self.parent.portfolio.get_instrument_diversification_multiplier()

    @input
    def get_forecast_diversification_multiplier(self, instrument_code):
        """
        Get the f.d.m from the previous module

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: dict of Tx1 pd.DataFrames

        """
        return self.parent.combForecast.get_monthly_forecast_diversification_multiplier(
            instrument_code)

    @input
    def get_instrument_weights(self):
        """
        Get instrument weights

        KEY INPUT

        :returns: Tx1 pd.DataFrame


        """

        return self.parent.portfolio.get_instrument_weights()

    @input
    def get_subsystem_position(self, instrument_code):
        """
        Get the position assuming all capital in one instruments, from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        """
        return self.parent.positionSize.get_subsystem_position(instrument_code)

    @input
    def get_actual_position(self, instrument_code):
        """
        Get the actual position from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        """
        return self.parent.portfolio.get_actual_position(instrument_code)

    @input
    def get_trading_rule_list(self, instrument_code):
        """
        Get the trading rules for this instrument, from a previous module

        KEY INPUT

        :returns: list of str

        """
        return self.parent.combForecast.get_trading_rule_list(instrument_code)

    @input
    def get_entire_trading_rule_list(self):
        """
        Get the trading rules for all instruments


        :returns: list of str

        """
        instrument_list = self.get_instrument_list()
        rules = [
            self.get_trading_rule_list(instrument_code)
            for instrument_code in instrument_list
        ]
        rules = sorted(sum(rules, []))

        return list(set(rules))

    @input
    def get_instrument_list(self):
        """
        Get the trading rules for this instrument, from a previous module

        :returns: list of str

        KEY INPUT

        """
        return self.parent.get_instrument_list()

    @input
    def get_notional_capital(self):
        """
        Get notional capital from the previous module

        FIXME: at some point will want to replace with 'actual' capital

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
        return self.parent.positionSize.get_daily_cash_vol_target()[
            "notional_trading_capital"
        ]

    @input
    def get_ann_risk_target(self):
        """
        Get annual risk target from the previous module

        KEY INPUT

        :returns: float
        """
        return (
            self.parent.positionSize.get_daily_cash_vol_target()[
                "percentage_vol_target"
            ]
            / 100.0
        )

    @input
    def get_fx_rate(self, instrument_code):
        """
        Get the FX rate from the previous module

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: Tx1 pd.DataFrames

        """

        return self.parent.positionSize.get_fx_rate(instrument_code)

    @input
    def get_notional_position(self, instrument_code):
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

    @input
    def get_buffers_for_position(self, instrument_code):
        """
        Get the buffered position from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx2 pd.DataFrame: columns top_pos, bot_pos

        KEY INPUT
        """

        return self.parent.portfolio.get_buffers_for_position(instrument_code)

    @input
    def get_actual_buffers_for_position(self, instrument_code):
        """
        Get the actual capital corrected buffered position from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx2 pd.DataFrame: columns top_pos, bot_pos

        KEY INPUT
        """

        return self.parent.portfolio.get_actual_buffers_for_position(
            instrument_code)

    @input
    def get_volatility_scalar(self, instrument_code):
        """
        Get the volatility scalar

        KEY INPUT

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        """

        return self.parent.positionSize.get_volatility_scalar(instrument_code)

    @diagnostic()
    def get_daily_price(self, instrument_code):
        """
        Get the instrument price from rawdata

        Cached as data isn't cached

        :param instrument_code:
        :type str:

        :returns: Tx1 pd.DataFrames

        """
        return self.parent.data.daily_prices(instrument_code)

    @diagnostic()
    def get_aligned_forecast(self, instrument_code, rule_variation_name):
        """
        Get the capped forecast aligned to daily prices


        KEY INPUT

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: Tx1 pd.DataFrames

        """
        price = self.get_daily_price(instrument_code)
        forecast = self.get_capped_forecast(
            instrument_code, rule_variation_name)

        forecast = forecast.reindex(price.index).ffill()

        return forecast

    @diagnostic()
    def get_aligned_subsystem_position(self, instrument_code):
        """
        Get the position assuming all capital in one instruments, aligned to price

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame


        """
        price = self.get_daily_price(instrument_code)
        sspos = self.get_subsystem_position(instrument_code)

        sspos = sspos.reindex(price.index).ffill()

        return sspos

    @input
    def get_value_of_price_move(self, instrument_code):
        """
        Get the value of a price move from raw data

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: float

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.get_value_of_price_move("EDOLLAR")
        2500
        """

        return self.parent.data.get_value_of_block_price_move(instrument_code)

    @diagnostic()
    def get_raw_cost_data(self, instrument_code: str) -> instrumentCosts:
        """
        Get the cost data for an instrument

        We cache this, because its coming from data so hasn't been cached yet

        KEY INPUT

        Execution slippage [half spread] price units
        Commission (local currency) per block
        Commission - percentage of value (0.01 is 1%)
        Commission (local currency) per block

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: dict of floats

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.get_raw_cost_data("EDOLLAR")['price_slippage']
        0.0025000000000000001

        """
        return self.parent.data.get_raw_cost_data(instrument_code)

    @diagnostic()
    def get_daily_returns_volatility(self, instrument_code):
        """
        Get the daily return (not %) volatility from previous stage, or calculate

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: Tx1 pd.DataFrames

        """

        system = self.parent
        if hasattr(system, "rawdata"):
            returns_vol = system.rawdata.daily_returns_volatility(
                instrument_code)
        else:
            price = self.get_daily_price(instrument_code)
            returns_vol = robust_vol_calc(price.diff())

        return returns_vol

    @diagnostic()
    def get_aligned_volatility_scalar(self, instrument_code):
        """
        Get the volatility scalar aligned to price

        KEY INPUT

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        """

        price = self.get_daily_price(instrument_code)
        vs = self.get_volatility_scalar(instrument_code)

        vs = vs.reindex(price.index).ffill()

        return vs

    @diagnostic()
    def get_instrument_scaling_factor(self, instrument_code):
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

        price = self.get_daily_price(instrument_code)

        return multiplier.reindex(price.index).ffill()

    @diagnostic()
    def get_forecast_scaling_factor(
            self,
            instrument_code,
            rule_variation_name):
        """
        Get forecast weight * FDM

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :param rule_variation_name: trading rule
        :type rule_variation_name: str

        :returns: Tx1 pd.DataFrame

        """

        fdm = self.get_forecast_diversification_multiplier(instrument_code)
        forecast_weights = self.get_forecast_weights(instrument_code)

        if rule_variation_name in forecast_weights.columns:

            fcast_weight_this_code = forecast_weights[rule_variation_name]
        else:
            fcast_weight_this_code = self.get_aligned_forecast(
                instrument_code, rule_variation_name
            )
            fcast_weight_this_code[:] = 0.0

        multiplier = fcast_weight_this_code * fdm

        return multiplier

    @diagnostic()
    def get_instrument_forecast_scaling_factor(
        self, instrument_code, rule_variation_name
    ):
        """
        Get forecast weight * FDM  *instrument_weight * IDM

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :param rule_variation_name: trading rule
        :type rule_variation_name: str

        :returns: Tx1 pd.DataFrame

        """

        fsf = self.get_forecast_scaling_factor(
            instrument_code, rule_variation_name)
        isf = self.get_instrument_scaling_factor(instrument_code)

        (fsf, isf) = fsf.align(isf, join="inner")

        return fsf * isf

    @diagnostic()
    def get_capital_in_rule(self, rule_variation_name):
        """
        Get sum of forecast weight * FDM  *instrument_weight * IDM for a given rule

        :param rule_variation_name: trading rule
        :type rule_variation_name: str

        :returns: Tx1 pd.DataFrame

        """

        instrument_list = self.get_instrument_list()
        all_risk_allocations = [
            self.get_instrument_forecast_scaling_factor(
                instrument_code, rule_variation_name
            )
            for instrument_code in instrument_list
        ]
        all_risk_allocations = pd.concat(all_risk_allocations, axis=1)

        return all_risk_allocations.sum(axis=1)

    @diagnostic()
    def get_buffered_position(self, instrument_code, roundpositions=True):
        """
        Get the buffered position

        :param instrument_code: instrument to get

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: Tx1 pd.DataFrame

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.get_buffered_position("EDOLLAR").tail(3)
                    position
        2015-12-09         1
        2015-12-10         1
        2015-12-11         1
        """

        self.log.msg("Calculating buffered positions")
        optimal_position = self.get_notional_position(instrument_code)
        pos_buffers = self.get_buffers_for_position(instrument_code)
        trade_to_edge = self.parent.config.buffer_trade_to_edge

        buffered_position = apply_buffer(
            optimal_position,
            pos_buffers,
            trade_to_edge=trade_to_edge,
            roundpositions=roundpositions,
        )

        buffered_position.columns = ["position"]

        return buffered_position
