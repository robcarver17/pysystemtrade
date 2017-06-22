from copy import copy
import pandas as pd
import numpy as np

from syscore.accounting import accountCurve, accountCurveGroup, weighted
from systems.basesystem import ALL_KEYNAME
from systems.defaults import system_defaults
from systems.system_cache import input, dont_cache, diagnostic, output
from systems.accounts_inputs import _AccountInput

from syscore.algos import apply_buffer
from syscore.genutils import TorF, str2Bool
from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.pdutils import turnover
from syscore.objects import resolve_function

ARBITRARY_FORECAST_CAPITAL = 100.0


class _AccountCosts(_AccountInput):
    """
    Partial SystemStage for accounting

    To avoid having one huge class built up from multiple bits

    This part deals with calculating costs and turnover
    """

    def _name(self):
        return "*do not use independently*"

    @diagnostic()
    def get_SR_cost(self, instrument_code):
        """
        Get the vol normalised SR costs for an instrument

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: float

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.get_SR_cost("EDOLLAR")
        0.0065584086244069775
        """

        raw_costs = self.get_raw_cost_data(instrument_code)
        block_value = self.get_value_of_price_move(instrument_code)

        price_slippage = raw_costs['price_slippage']
        value_of_block_commission = raw_costs['value_of_block_commission']
        percentage_cost = raw_costs['percentage_cost']
        value_of_pertrade_commission = raw_costs[
            'value_of_pertrade_commission']

        daily_vol = self.get_daily_returns_volatility(instrument_code)
        daily_price = self.get_daily_price(instrument_code)

        last_date = daily_price.index[-1]
        start_date = last_date - pd.DateOffset(years=1)
        average_price = float(daily_price[start_date:].mean())
        average_vol = float(daily_vol[start_date:].mean())

        # Cost in Sharpe Ratio terms
        # First work out costs in price terms
        price_block_commission = value_of_block_commission / block_value
        price_percentage_cost = average_price * percentage_cost
        price_per_trade_cost = value_of_pertrade_commission / \
            block_value  # assume one trade per contract

        price_total = price_slippage + price_block_commission + \
            price_percentage_cost + price_per_trade_cost

        avg_annual_vol = average_vol * ROOT_BDAYS_INYEAR

        SR_cost = 2.0 * price_total / (avg_annual_vol)

        return SR_cost

    @diagnostic()
    def get_cash_costs(self, instrument_code):
        """
        Get the cash costs for an instrument

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: 3 tuple of floats: value_total_per_block, value_of_pertrade_commission, percentage_cost

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.get_cash_costs("EDOLLAR")
        (8.3599999999999994, 0, 0)
        """

        raw_costs = self.get_raw_cost_data(instrument_code)
        block_value = self.get_value_of_price_move(instrument_code)

        price_slippage = raw_costs['price_slippage']
        value_of_block_commission = raw_costs['value_of_block_commission']
        percentage_cost = raw_costs['percentage_cost']
        value_of_pertrade_commission = raw_costs[
            'value_of_pertrade_commission']

        # Cost in actual terms in local currency
        value_of_slippage = price_slippage * block_value
        value_total_per_block = value_of_block_commission + value_of_slippage

        cash_costs = (value_total_per_block, value_of_pertrade_commission,
                      percentage_cost)

        return cash_costs

    @dont_cache
    def get_costs(self, instrument_code):
        """
        Get the relevant kinds of cost for an instrument

        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: 2 tuple
        """

        use_SR_costs = str2Bool(self.parent.config.use_SR_costs)

        if use_SR_costs:
            return (self.get_SR_cost(instrument_code), None)
        else:
            return (None, self.get_cash_costs(instrument_code))

    @diagnostic()
    def subsystem_turnover(self, instrument_code, roundpositions=True):
        """
        Get the annualised turnover for an instrument subsystem

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: float


        """

        positions = self.get_aligned_subsystem_position(instrument_code)
        average_position_for_turnover = self.get_aligned_volatility_scalar(
            instrument_code)

        return turnover(positions, average_position_for_turnover)

    @diagnostic()
    def subsystem_SR_costs(self, instrument_code, roundpositions=False):
        """
        Get the annualised SR costs for an instrument subsystem

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: float




        """

        SR_cost_per_turnover = self.get_SR_cost(instrument_code)

        turnover_for_SR = self.subsystem_turnover(
            instrument_code, roundpositions=roundpositions)
        SR_cost = SR_cost_per_turnover * turnover_for_SR

        return SR_cost

    @diagnostic()
    def instrument_turnover(self, instrument_code, roundpositions=True):
        """
        Get the annualised turnover for an instrument

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float


        """
        average_position_for_turnover = self.get_aligned_volatility_scalar(
            instrument_code) * self.get_instrument_scaling_factor(
                instrument_code)

        positions = self.get_buffered_position(
            instrument_code, roundpositions=roundpositions)

        return turnover(positions, average_position_for_turnover)

    @diagnostic()
    def forecast_turnover_for_list(self, instrument_code_list,
                                   rule_variation_name):
        """
        Get the average turnover for a rule, over instrument_code_list

        :param instrument_code_list: instruments to get values for
        :type instrument_code_list: list of str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float

        """

        average_forecast_for_turnover = system_defaults[
            'average_absolute_forecast']

        forecast_list = [
            self.get_capped_forecast(instrument_code, rule_variation_name)
            for instrument_code in instrument_code_list
        ]

        turnovers = [
            turnover(forecast, average_forecast_for_turnover)
            for forecast in forecast_list
        ]

        if len(instrument_code_list) == 1:
            return turnovers[0]

        # weight by length
        forecast_lengths = [len(forecast.index) for forecast in forecast_list]
        total_length = sum(forecast_lengths)
        weighted_turnovers = [
            tover * fc_length / total_length
            for (tover, fc_length) in zip(turnovers, forecast_lengths)
        ]

        avg_turnover = sum(weighted_turnovers)

        return avg_turnover

    @diagnostic()
    def forecast_turnover(self, instrument_code, rule_variation_name):
        """
        Get the annualised turnover for a forecast/rule combination

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float


        """

        use_pooled_turnover = str2Bool(
            self.parent.config.forecast_cost_estimates['use_pooled_turnover'])

        if use_pooled_turnover:
            instrument_code_list = self.has_same_rules_as_code(instrument_code)
        else:
            instrument_code_list = [instrument_code]

        turnover_for_SR = self.forecast_turnover_for_list(
            instrument_code_list, rule_variation_name)

        return turnover_for_SR

    @diagnostic()
    def get_SR_cost_instr_forecast_for_list(self, instrument_code_list,
                                            rule_variation_name):
        """
        Get the SR cost for a forecast/rule combination, averaged across multiple instruments

        :param instrument_code_list: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float


        """

        turnover_list = [
            self.forecast_turnover(instrument_code, rule_variation_name)
            for instrument_code in instrument_code_list
        ]

        SR_cost_per_turnover = [
            self.get_SR_cost(instrument_code)
            for instrument_code in instrument_code_list
        ]

        forecast_list = [
            self.get_capped_forecast(instrument_code, rule_variation_name)
            for instrument_code in instrument_code_list
        ]

        SR_cost = [
            tover * SRcpt
            for (tover, SRcpt) in zip(turnover_list, SR_cost_per_turnover)
        ]

        # weight by length
        forecast_lengths = [len(forecast.index) for forecast in forecast_list]
        total_length = sum(forecast_lengths)
        weighted_SR_costs = [
            SRc * fc_length / total_length
            for (SRc, fc_length) in zip(SR_cost, forecast_lengths)
        ]

        avg_SR_cost = sum(weighted_SR_costs)

        return avg_SR_cost

    @diagnostic()
    def get_SR_cost_for_instrument_forecast(self, instrument_code,
                                            rule_variation_name):
        """
        Get the SR cost for a forecast/rule combination

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float

        KEY OUTPUT
        """

        use_pooled_costs = self.parent.config.forecast_cost_estimates[
            'use_pooled_costs']

        if use_pooled_costs:
            instrument_code_list = self.has_same_rules_as_code(instrument_code)
            SR_cost = self.get_SR_cost_instr_forecast_for_list(
                instrument_code_list, rule_variation_name)

        else:
            # note the turnover may still be pooled..
            SR_cost = self.forecast_turnover(
                instrument_code,
                rule_variation_name) * self.get_SR_cost(instrument_code)

        return SR_cost


class _AccountInstrumentForecast(_AccountCosts):
    """
    Partial SystemStage for accounting

    To avoid having one huge class built up from multiple bits

    This part deals with p&l for one instrument and forecast; the building block of most other p&l
    """

    @diagnostic(not_pickable=True)
    def pandl_for_instrument_forecast(self,
                                      instrument_code,
                                      rule_variation_name,
                                      delayfill=True):
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
            "Calculating pandl for instrument forecast for %s %s" %
            (instrument_code, rule_variation_name),
            instrument_code=instrument_code,
            rule_variation_name=rule_variation_name)

        # by construction all these things are aligned
        price = self.get_daily_price(instrument_code)
        forecast = self.get_aligned_forecast(instrument_code,
                                             rule_variation_name)
        get_daily_returns_volatility = self.get_daily_returns_volatility(
            instrument_code)

        # We NEVER use cash costs for forecasts ...
        SR_cost = self.get_SR_cost_for_instrument_forecast(
            instrument_code, rule_variation_name)

        # We use percentage returns (as no 'capital') and don't round
        # positions
        pandl_fcast = accountCurve(
            price,
            forecast=forecast,
            delayfill=delayfill,
            roundpositions=False,
            value_of_price_point=1.0,
            capital=ARBITRARY_FORECAST_CAPITAL,
            SR_cost=SR_cost,
            cash_costs=None,
            get_daily_returns_volatility=get_daily_returns_volatility)

        return pandl_fcast

    @diagnostic(not_pickable=True)
    def pandl_for_instrument_forecast_weighted(self,
                                               instrument_code,
                                               rule_variation_name,
                                               delayfill=True):
        """
        Get the p&l for one instrument and forecast; as % of total capital


        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurve


        """

        self.log.msg(
            "Calculating pandl for instrument forecast weighted for %s %s" %
            (instrument_code, rule_variation_name),
            instrument_code=instrument_code,
            rule_variation_name=rule_variation_name)

        pandl = self.pandl_for_instrument_forecast(
            instrument_code, rule_variation_name, delayfill=delayfill)
        weight = self.get_instrument_forecast_scaling_factor(
            instrument_code, rule_variation_name)
        pandl = weighted(pandl, weight)

        return pandl


class _AccountInstruments(_AccountInstrumentForecast):
    """
    Partial SystemStage for accounting

    To avoid having one huge class built up from multiple bits

    This part deals with p&l for instruments
    """

    def _name(self):
        return "*do not use independently*"

    @diagnostic(not_pickable=True)
    def pandl_for_subsystem(self,
                            instrument_code,
                            delayfill=True,
                            roundpositions=False):
        """
        Get the p&l for one instrument

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: accountCurve

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.pandl_for_subsystem("US10", percentage=True).ann_std()
        0.23422378634127036
        """

        self.log.msg(
            "Calculating pandl for subsystem for instrument %s" %
            instrument_code,
            instrument_code=instrument_code)

        price = self.get_daily_price(instrument_code)
        positions = self.get_aligned_subsystem_position(instrument_code)

        fx = self.get_fx_rate(instrument_code)

        value_of_price_point = self.get_value_of_price_move(instrument_code)
        get_daily_returns_volatility = self.get_daily_returns_volatility(
            instrument_code)

        (SR_cost, cash_costs) = self.get_costs(instrument_code)

        capital = self.get_notional_capital()
        ann_risk_target = self.get_ann_risk_target()

        instr_pandl = accountCurve(
            price,
            positions=positions,
            delayfill=delayfill,
            roundpositions=roundpositions,
            fx=fx,
            value_of_price_point=value_of_price_point,
            capital=capital,
            SR_cost=SR_cost,
            cash_costs=cash_costs,
            get_daily_returns_volatility=get_daily_returns_volatility,
            ann_risk_target=ann_risk_target)

        return instr_pandl

    @output(not_pickable=True)
    def pandl_across_subsystems(self, delayfill=True, roundpositions=False):
        """
        Get the p&l across subsystems (unweighted)

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: accountCurve

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.pandl_across_subsystems().to_frame().tail(5)
                     EDOLLAR      US10
        2015-12-07  0.001191 -0.005012
        2015-12-08  0.000448 -0.002395
        2015-12-09  0.000311 -0.002797
        2015-12-10 -0.002384  0.003957
        2015-12-11  0.004835 -0.007594
        """

        # Subsystems use entire capital
        capital = self.get_notional_capital()

        instruments = self.get_instrument_list()
        pandl_across_subsys = [
            self.pandl_for_subsystem(
                instrument_code,
                delayfill=delayfill,
                roundpositions=roundpositions)
            for instrument_code in instruments
        ]

        pandl = accountCurveGroup(
            pandl_across_subsys,
            instruments,
            capital=capital,
            weighted_flag=False)

        return pandl

    @diagnostic(not_pickable=True)
    def pandl_for_instrument(self,
                             instrument_code,
                             delayfill=True,
                             roundpositions=True):
        """
        Get the p&l for one instrument

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: accountCurve

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>> system.accounts.pandl_for_instrument("US10").ann_std()
        0.13908407620762306
        """

        self.log.msg(
            "Calculating pandl for instrument for %s" % instrument_code,
            instrument_code=instrument_code)

        price = self.get_daily_price(instrument_code)
        positions = self.get_buffered_position(
            instrument_code, roundpositions=roundpositions)
        fx = self.get_fx_rate(instrument_code)
        value_of_price_point = self.get_value_of_price_move(instrument_code)
        get_daily_returns_volatility = self.get_daily_returns_volatility(
            instrument_code)

        capital = self.get_notional_capital()
        ann_risk_target = self.get_ann_risk_target()

        (SR_cost, cash_costs) = self.get_costs(instrument_code)

        instr_pandl = accountCurve(
            price,
            positions=positions,
            delayfill=delayfill,
            roundpositions=roundpositions,
            fx=fx,
            value_of_price_point=value_of_price_point,
            capital=capital,
            ann_risk_target=ann_risk_target,
            SR_cost=SR_cost,
            cash_costs=cash_costs,
            get_daily_returns_volatility=get_daily_returns_volatility)

        if SR_cost is not None:
            # Note that SR cost is done as a proportion of capital
            # Since we're only using part of the capital we need to correct
            # for this
            turnover_for_SR = self.instrument_turnover(
                instrument_code, roundpositions=roundpositions)
            SR_cost = SR_cost * turnover_for_SR
            weighting = self.get_instrument_scaling_factor(instrument_code)
            apply_weight_to_costs_only = True

            instr_pandl = weighted(
                instr_pandl,
                weighting=weighting,
                apply_weight_to_costs_only=apply_weight_to_costs_only)

        else:
            # Costs wil be correct
            # We don't need to do anything
            pass

        return instr_pandl

    @output(not_pickable=True)
    def pandl_for_instrument_rules(self, instrument_code, delayfill=True):
        """
        Get the p&l for one instrument over multiple forecasts; as % of arbitrary capital

        P&L are weighted by forecast weights and FDM

        KEY OUTPUT

        :param instrument_code: instrument to get values for
        :type instrument_code: str


        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurve

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.pandl_for_instrument_rules_weighted("EDOLLAR").get_stats("sharpe")
        {'ewmac16': 0.6799720823590352, 'ewmac8': 0.69594671177102}
        """

        self.log.terse(
            "Calculating pandl for instrument rules for %s" % instrument_code,
            instrument_code=instrument_code)

        forecast_rules = self.get_trading_rule_list(instrument_code)
        pandl_rules_unweighted = [
            self.pandl_for_instrument_forecast(
                instrument_code, rule_variation_name, delayfill=delayfill)
            for rule_variation_name in forecast_rules
        ]

        pandl_rules = [
            weighted(
                pandl_this_rule,
                weighting=self.get_forecast_scaling_factor(
                    instrument_code, rule_variation_name))
            for (pandl_this_rule, rule_variation_name
                 ) in zip(pandl_rules_unweighted, forecast_rules)
        ]

        pandl_rules = accountCurveGroup(
            pandl_rules,
            forecast_rules,
            capital=ARBITRARY_FORECAST_CAPITAL,
            weighted_flag=True)

        return pandl_rules


class _AccountTradingRules(_AccountInstrumentForecast):
    """
    Partial SystemStage for accounting

    To avoid having one huge class built up from multiple bits

    This part deals with accounting for trading rules
    """

    def _name(self):
        return "*do not use independently*"

    @diagnostic(not_pickable=True)
    def pandl_for_all_trading_rules(self, delayfill=True):
        """
        Get the p&l for all trading rules; as % of total capital

        Each trading rule is weighted as a proportion of total capital

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurveGroup

        """

        self.log.terse("Calculating pandl for all trading rules")

        variations = self.get_entire_trading_rule_list()

        # already weighted, don't need to do again
        pandl_by_trading_rule_weighted = [
            self.pandl_for_trading_rule_weighted(rulename, delayfill)
            for rulename in variations
        ]

        # this is a group of groups... will it work?
        pandl_all_rules = accountCurveGroup(
            pandl_by_trading_rule_weighted,
            variations,
            capital=ARBITRARY_FORECAST_CAPITAL,
            weighted_flag=True)

        return pandl_all_rules

    @diagnostic(not_pickable=True)
    def pandl_for_all_trading_rules_unweighted(self, delayfill=True):
        """
        Get the p&l for all trading rules; unweighted

        Each trading rule has capital in isolation

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurveGroup

        """

        self.log.terse("Calculating pandl for all trading rules unweighted")

        variations = self.get_entire_trading_rule_list()

        # already weighted, don't need to do again
        pandl_by_trading_rule_unweighted = [
            self.pandl_for_trading_rule(rulename, delayfill)
            for rulename in variations
        ]

        # this is a group of groups... will it work?
        pandl_all_rules = accountCurveGroup(
            pandl_by_trading_rule_unweighted,
            variations,
            capital=ARBITRARY_FORECAST_CAPITAL,
            weighted_flag=False)

        return pandl_all_rules

    @diagnostic(not_pickable=True)
    def pandl_for_trading_rule_unweighted(self,
                                          rule_variation_name,
                                          delayfill=True):
        """
        Get the p&l for one trading rule over multiple instruments; as % of arbitrary capital

        Within the trading rule the instrument returns are NOT weighted by instrument weight

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurve

        """

        self.log.terse("Calculating pandl for trading rule (unweighted) %s" %
                       rule_variation_name)

        instrument_list = self.parent.get_instrument_list()
        instrument_list = [
            instr_code for instr_code in instrument_list
            if rule_variation_name in self.get_trading_rule_list(instr_code)
        ]

        pandl_by_instrument = [
            self.pandl_for_instrument_forecast(instr_code, rule_variation_name,
                                               delayfill)
            for instr_code in instrument_list
        ]

        pandl_rule = accountCurveGroup(
            pandl_by_instrument,
            instrument_list,
            capital=ARBITRARY_FORECAST_CAPITAL,
            weighted_flag=False)

        return pandl_rule

    @diagnostic(not_pickable=True)
    def pandl_for_trading_rule(self, rule_variation_name, delayfill=True):
        """
        Get the p&l for one trading rule over multiple instruments; as % of its risk contribution

        Within the trading rule the instrument returns are weighted by instrument weight

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurve

        """

        self.log.terse(
            "Calculating pandl for trading rule %s" % rule_variation_name)

        instrument_list = self.parent.get_instrument_list()
        instrument_list = [
            instr_code for instr_code in instrument_list
            if rule_variation_name in self.get_trading_rule_list(instr_code)
        ]

        # already weighted
        # capital on these will be the default
        pandl_by_instrument_weighted = [
            self.pandl_for_instrument_forecast_weighted(
                instr_code, rule_variation_name, delayfill)
            for instr_code in instrument_list
        ]

        # now we weight so total capital is correct
        capital_this_rule = self.get_capital_in_rule(rule_variation_name)

        def _cleanweightelement(capelement):
            if np.isnan(capelement):
                return 0.0
            if capelement == 0.0:
                return 0.0
            else:
                return 1.0 / capelement

        weight = [
            _cleanweightelement(capelement)
            for capelement in list(capital_this_rule.values)
        ]
        weight = pd.Series(weight, index=capital_this_rule.index)

        pandl_by_instrument_reweighted = [
            weighted(pandl_for_instrument, weight, allow_reweighting=True)
            for pandl_for_instrument in pandl_by_instrument_weighted
        ]

        pandl_rule = accountCurveGroup(
            pandl_by_instrument_reweighted,
            instrument_list,
            capital=ARBITRARY_FORECAST_CAPITAL,
            weighted_flag=True)

        return pandl_rule

    @diagnostic(not_pickable=True)
    def pandl_for_trading_rule_weighted(self,
                                        rule_variation_name,
                                        delayfill=True):
        """
        Get the p&l for one trading rule over multiple instruments; as % of total capital

        Within the trading rule the instrument returns are weighted by risk contribution

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurveGroup

        """
        self.log.terse(
            "Calculating pandl for trading rule %s" % rule_variation_name)

        instrument_list = self.parent.get_instrument_list()
        instrument_list = [
            instr_code for instr_code in instrument_list
            if rule_variation_name in self.get_trading_rule_list(instr_code)
        ]

        # already weighted, don't need to do again
        pandl_by_instrument_weighted = [
            self.pandl_for_instrument_forecast_weighted(
                instr_code, rule_variation_name, delayfill)
            for instr_code in instrument_list
        ]

        pandl_rule = accountCurveGroup(
            pandl_by_instrument_weighted,
            instrument_list,
            capital=ARBITRARY_FORECAST_CAPITAL,
            weighted_flag=True)

        return pandl_rule

    @output(not_pickable=True)
    def pandl_for_instrument_rules_unweighted(self,
                                              instrument_code,
                                              rule_list=None,
                                              delayfill=True):
        """
        Get the p&l for one instrument over multiple forecasts; as % of arbitrary capital

        All forecasting rules will have same expected std dev of returns; these aren't weighted

        KEY OUTPUT

        :param instrument_code: instrument to get values for
        :type instrument_code: str


        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurveGroup

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.pandl_for_instrument_rules_unweighted("EDOLLAR").get_stats("sharpe")
        {'ewmac16': 0.6799720823590352, 'ewmac8': 0.69594671177102}
        """

        self.log.terse(
            "Calculating pandl for instrument rules for %s" % instrument_code,
            instrument_code=instrument_code)

        if rule_list is None:
            rule_list = self.get_trading_rule_list(instrument_code)
        pandl_rules = [
            self.pandl_for_instrument_forecast(
                instrument_code, rule_variation_name, delayfill=delayfill)
            for rule_variation_name in rule_list
        ]

        pandl_rules = accountCurveGroup(
            pandl_rules,
            rule_list,
            capital=ARBITRARY_FORECAST_CAPITAL,
            weighted_flag=False)

        return pandl_rules


class _AccountActual(_AccountCosts):
    """
    Partial SystemStage for accounting

    To avoid having one huge class built up from multiple bits

    This part deals with 'actual' accounts and positions, where we've applied a capital scalar
    See blog post: http://qoppac.blogspot.co.uk/2016/06/capital-correction-pysystemtrade.html
    """

    def _name(self):
        return "*do not use independently*"

    @diagnostic()
    def capital_multiplier(self, delayfill=True, roundpositions=False):
        """
        Get a capital multiplier

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: pd.Series

        """
        system = self.parent
        capmult_params = copy(system.config.capital_multiplier)
        capmult_func = resolve_function(capmult_params.pop("func"))

        capmult = capmult_func(system, **capmult_params)

        capmult = capmult.reindex(self.portfolio().index).ffill()

        return capmult

    @diagnostic()
    def get_actual_capital(self, delayfill=True, roundpositions=False):
        """
        Get a capital multiplier multiplied by notional capital

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: pd.Series

        """

        capmult = self.capital_multiplier()
        notional = self.get_notional_capital()

        if not isinstance(notional, pd.core.series.Series):
            notional_ts = pd.Series([notional] * len(capmult), capmult.index)
        else:
            notional_ts = notional.reindex(capmult.index).ffill()

        capital = capmult * notional_ts

        return capital

    @diagnostic()
    def get_buffered_position_with_multiplier(self,
                                              instrument_code,
                                              roundpositions=True):
        """
        Get the buffered position

        :param instrument_code: instrument to get

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: Tx1 pd.DataFrame

        """

        self.log.msg("Calculating buffered positions with multiplier")
        optimal_position = self.get_actual_position(instrument_code)
        pos_buffers = self.get_actual_buffers_for_position(instrument_code)
        trade_to_edge = self.parent.config.buffer_trade_to_edge

        buffered_position = apply_buffer(
            optimal_position,
            pos_buffers,
            trade_to_edge=trade_to_edge,
            roundpositions=roundpositions)

        buffered_position.columns = ["position"]

        return buffered_position

    @diagnostic(not_pickable=True)
    def pandl_for_instrument_with_multiplier(self,
                                             instrument_code,
                                             delayfill=True,
                                             roundpositions=True):
        """
        Get the p&l for one instrument, using variable capital

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: accountCurve

        """

        self.log.msg(
            "Calculating pandl for instrument for %s with capital multiplier" %
            instrument_code,
            instrument_code=instrument_code)

        price = self.get_daily_price(instrument_code)
        positions = self.get_buffered_position_with_multiplier(
            instrument_code, roundpositions=roundpositions)
        fx = self.get_fx_rate(instrument_code)
        value_of_price_point = self.get_value_of_price_move(instrument_code)
        get_daily_returns_volatility = self.get_daily_returns_volatility(
            instrument_code)

        capital = self.get_actual_capital(
            delayfill=delayfill, roundpositions=roundpositions)

        ann_risk_target = self.get_ann_risk_target()

        (SR_cost, cash_costs) = self.get_costs(instrument_code)

        instr_pandl = accountCurve(
            price,
            positions=positions,
            delayfill=delayfill,
            roundpositions=roundpositions,
            fx=fx,
            value_of_price_point=value_of_price_point,
            capital=capital,
            ann_risk_target=ann_risk_target,
            SR_cost=SR_cost,
            cash_costs=cash_costs,
            get_daily_returns_volatility=get_daily_returns_volatility)

        if SR_cost is not None:
            # Note that SR cost is done as a proportion of capital
            # Since we're only using part of the capital we need to correct
            # for this
            turnover_for_SR = self.instrument_turnover(
                instrument_code, roundpositions=roundpositions)
            SR_cost = SR_cost * turnover_for_SR
            weighting = self.get_instrument_scaling_factor(instrument_code)
            apply_weight_to_costs_only = True

            instr_pandl = weighted(
                instr_pandl,
                weighting=weighting,
                apply_weight_to_costs_only=apply_weight_to_costs_only)

        else:
            # Costs wil be correct
            # We don't need to do anything
            pass

        return instr_pandl

    @diagnostic(not_pickable=True)
    def portfolio_with_multiplier(self, delayfill=True, roundpositions=True):
        """
        Get the p&l for entire portfolio using multiplied "actual" capital

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: accountCurve

        """

        self.log.terse("Calculating pandl for portfolio")
        capital = self.get_actual_capital(delayfill, roundpositions)
        instruments = self.get_instrument_list()
        port_pandl = [
            self.pandl_for_instrument_with_multiplier(
                instrument_code,
                delayfill=delayfill,
                roundpositions=roundpositions)
            for instrument_code in instruments
        ]

        port_pandl = accountCurveGroup(
            port_pandl, instruments, capital=capital, weighted_flag=True)

        return port_pandl


class Account(_AccountActual, _AccountTradingRules, _AccountInstruments):
    """
    SystemStage for accounting

    To avoid having one huge class built up from multiple bits

    Name: accounts
    """

    def _name(self):
        return "accounts"

    @output(not_pickable=True)
    def portfolio(self, delayfill=True, roundpositions=True):
        """
        Get the p&l for entire portfolio

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: accountCurve

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.portfolio().ann_std()
        0.2638225179274214
        """

        self.log.terse("Calculating pandl for portfolio")
        capital = self.get_notional_capital()
        instruments = self.get_instrument_list()
        port_pandl = [
            self.pandl_for_instrument(
                instrument_code,
                delayfill=delayfill,
                roundpositions=roundpositions)
            for instrument_code in instruments
        ]

        port_pandl = accountCurveGroup(
            port_pandl, instruments, capital=capital, weighted_flag=True)

        return port_pandl


if __name__ == '__main__':
    import doctest
    doctest.testmod()
