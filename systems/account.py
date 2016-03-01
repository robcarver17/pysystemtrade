import pandas as pd

from syscore.accounting import accountCurve, accountCurveGroup
from systems.stage import SystemStage
from systems.basesystem import ALL_KEYNAME
from syscore.algos import robust_vol_calc
from syscore.genutils import TorF


class Account(SystemStage):
    """
    SystemStage for accounting

    KEY INPUTS:
        system.forecastScaleCap.get_capped_forecast()
            found in self.get_capped_forecast()

        system.get_instrument_list()
            found in self.get_instrument_list()

        system.positionSize.get_subsystem_position(instrument_code)
            found in self.get_subsystem_position()

        system.positionSize.get_daily_cash_vol_target()
            found in self.get_daily_cash_vol_target() and self.get_ann_risk_target()

        system.positionSize.get_fx_rate()
            found in self.get_fx_rate()

        system.portfolio.get_notional_position()
            found in self.get_notional_position()

        system.data.daily_prices(instrument_code)
            found in self.get_daily_price()

        system.positionSize.get_instrument_sizing_data()
            found in self.get_value_of_price_move()

        system.rawdata.daily_returns_volatility() or system.data.daily_prices(instrument_code)
            found in self.get_daily_returns_volatility()

    KEY OUTPUTS: Used for optimisation:
                 system.accounts.pandl_for_instrument_rules
                 system.accounts.accounts.pandl_across_subsystems

    NOTE - there are many unused methods in this function - reserved for future use

    Name: accounts
    """

    def __init__(self):
        """
        Create a SystemStage for accounting



        """

        protected = []
        setattr(self, "_protected", protected)

        setattr(self, "name", "accounts")

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
            instrument_code, rule_variation_name)

    def get_forecast_weights(self, instrument_code):
        """
        Get the capped forecast from the previous module

        NOT USED YET

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: dict of Tx1 pd.DataFrames

        """
        return self.parent.combForecast.get_forecast_weights(instrument_code)

    def get_instrument_div_multiplier(self):
        """
        Get instrument div mult

        :returns: Tx1 pd.DataFrame

        NOT USED YET


        """

        return self.parent.portfolio.get_instrument_diversification_multiplier()

    def get_forecast_div_multiplier(self, instrument_code):
        """
        Get the f.d.m from the previous module

        NOT USED YET

        :param instrument_code:
        :type str:

        :returns: dict of Tx1 pd.DataFrames

        """
        return self.parent.combForecast.get_forecast_diversification_multiplier(
            instrument_code)

    def get_instrument_weights(self):
        """
        Get instrument weights


        :returns: Tx1 pd.DataFrame

        NOT USED YET


        """

        return self.parent.portfolio.get_instrument_weights()

    def get_subsystem_position(self, instrument_code):
        """
        Get the position assuming all capital in one instruments, from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        """
        return self.parent.positionSize.get_subsystem_position(instrument_code)


    def get_trading_rules(self):
        """
        Get the trading rules for this instrument, from a previous module


        :returns: list of str

        NOT USED YET
        """
        return list(self.parent.rules.trading_rules().keys())

    def get_instrument_list(self):
        """
        Get the trading rules for this instrument, from a previous module

        :returns: list of str

        KEY INPUT

        """
        return self.parent.get_instrument_list()

    def get_rule_groups(self):
        """
        Get the rule groups from the config

        NOT USED YET

        :returns: nested dict
        """
        return getattr(self.parent.config, "rule_groups", dict())

    def get_style_groups(self):
        """
        Get the style groups from the config

        :returns: nested dict

        NOT USED YET

        """
        return getattr(self.parent.config, "style_groups", dict())

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
            'notional_trading_capital']

    def get_ann_risk_target(self):
        """
        Get annual risk target from the previous module

        KEY INPUT

        :returns: float
        """
        return self.parent.positionSize.get_daily_cash_vol_target()['percentage_vol_target']/100.0

    def get_fx_rate(self, instrument_code):
        """
        Get the FX rate from the previous module

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: Tx1 pd.DataFrames

        """

        return self.parent.positionSize.get_fx_rate(instrument_code)

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

    def get_daily_price(self, instrument_code):
        """
        Get the daily instrument price from rawdata

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: Tx1 pd.DataFrames

        """
        def _get_daily_price(system, instrument_code):
            return system.data.daily_prices(instrument_code)

        instrument_price = self.parent.calc_or_cache(
            'get_daily_price', instrument_code, _get_daily_price)

        return instrument_price

    def get_value_of_price_move(self, instrument_code):
        """
        Get the value of a price move from the previous module

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

        (not_used, value_of_price_move) = self.parent.positionSize.get_instrument_sizing_data(
            instrument_code)

        return value_of_price_move

    def get_daily_returns_volatility(self, instrument_code):
        """
        Get the daily return (not %) volatility from previous stage, or calculate

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: Tx1 pd.DataFrames

        """

        def _get_daily_returns_volatility(system, instrument_code):
            if hasattr(system, "rawdata"):
                returns_vol = system.rawdata.daily_returns_volatility(
                    instrument_code)
            else:
                price = self.get_daily_price(instrument_code)
                returns_vol = robust_vol_calc(price.diff())

            return returns_vol

        price_volatility = self.parent.calc_or_cache(
            'get_daily_returns_volatility', instrument_code, _get_daily_returns_volatility)

        return price_volatility

    

    def pandl_for_subsystem(

            self, instrument_code, percentage=True, delayfill=True, roundpositions=False):
        """
        Get the p&l for one instrument

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param percentage: Return results as % of total notional capital
        :type percentage: bool

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
        0.23486418072398296
        """

        def _pandl_for_subsystem(
                system, instrument_code, this_stage, percentage, delayfill, roundpositions):

            this_stage.log.msg("Calculating pandl for subsystem for instrument %s" % instrument_code,
                               instrument_code=instrument_code)

            price = this_stage.get_daily_price(instrument_code)
            positions = this_stage.get_subsystem_position(instrument_code)
            fx = this_stage.get_fx_rate(instrument_code)
            value_of_price_point = this_stage.get_value_of_price_move(
                instrument_code)
            get_daily_returns_volatility = this_stage.get_daily_returns_volatility(
                instrument_code)

            ## FIX ME place holder
            cost_per_block=None
            SR_cost=0.0
            
            capital = this_stage.get_notional_capital()
            ann_risk_target = this_stage.get_ann_risk_target()

            instr_pandl = accountCurve(price, positions=positions, delayfill=delayfill, 
                                       roundpositions=roundpositions,
                                fx=fx, value_of_price_point=value_of_price_point, capital=capital,
                                percentage=percentage, SR_cost=SR_cost, cost_per_block=cost_per_block,
                                get_daily_returns_volatility=get_daily_returns_volatility,
                                ann_risk_target = ann_risk_target)

            return instr_pandl

        itemname = "pandl_for_subsystem__percentage%sdelayfill%sroundpositions%s" % (
            TorF(percentage), TorF(delayfill), TorF(roundpositions))
        instr_pandl = self.parent.calc_or_cache(
            itemname, instrument_code, _pandl_for_subsystem, self, percentage, delayfill, roundpositions)

        return instr_pandl


    def pandl_across_subsystems(
                                self, percentage=True, delayfill=True, roundpositions=False):
        """
        Get the p&l across subsystems

        :param percentage: Return results as % of total notional capital
        :type percentage: bool

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
        >>> system.accounts.pandl_across_subsystems(percentage=True).to_frame().tail(5)
                     EDOLLAR      US10
        2015-12-07  0.001191 -0.005012
        2015-12-08  0.000448 -0.002395
        2015-12-09  0.000311 -0.002797
        2015-12-10 -0.002384  0.003957
        2015-12-11  0.004835 -0.007594
        """
        def _pandl_across_subsystems(
                system, instrumentCodeNotUsed, this_stage, percentage, delayfill, roundpositions):

            instruments = this_stage.get_instrument_list()
            pandl_across_subsys = [
                this_stage.pandl_for_subsystem(
                    instrument_code,
                    percentage=percentage,
                    delayfill=delayfill,
                    roundpositions=roundpositions) for instrument_code in instruments]
            
            pandl = accountCurveGroup(pandl_across_subsys, instruments)
            
            return pandl

        itemname = "pandl_across_subsystems__percentage%sdelayfill%sroundpositions%s" % (
            TorF(percentage), TorF(delayfill), TorF(roundpositions))
        instr_pandl = self.parent.calc_or_cache(
            itemname, ALL_KEYNAME, _pandl_across_subsystems, self, percentage, delayfill, roundpositions)

        return instr_pandl


    def pandl_for_instrument(
            self, instrument_code, percentage=True, delayfill=True, roundpositions=False):
        """
        Get the p&l for one instrument

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param percentage: Return results as % of total notional capital
        :type percentage: bool

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: accountCurve

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>> system.accounts.pandl_for_instrument("US10", percentage=True).ann_std()
        0.14091850843438977
        """

        def _pandl_for_instrument(
                system, instrument_code, this_stage, percentage, delayfill, roundpositions):

            this_stage.log.msg("Calculating pandl for instrument for %s" % instrument_code,
                               instrument_code=instrument_code)
            
            price = this_stage.get_daily_price(instrument_code)
            positions = this_stage.get_notional_position(instrument_code)
            fx = this_stage.get_fx_rate(instrument_code)
            value_of_price_point = this_stage.get_value_of_price_move(
                instrument_code)
            get_daily_returns_volatility = this_stage.get_daily_returns_volatility(
                instrument_code)

            capital = this_stage.get_notional_capital()
            ann_risk_target = this_stage.get_ann_risk_target()


            ## FIX ME place holder
            cost_per_block=None
            SR_cost=0.0

            instr_pandl = accountCurve(price, positions=positions, delayfill=delayfill, 
                                       roundpositions=roundpositions,
                                fx=fx, value_of_price_point=value_of_price_point, capital=capital,
                                ann_risk_target = ann_risk_target,
                                percentage=percentage, SR_cost=SR_cost, cost_per_block=cost_per_block,
                                get_daily_returns_volatility=get_daily_returns_volatility)

            return instr_pandl

        itemname = "pandl_for_instrument__percentage%sdelayfill%sroundpositions%s" % (
            TorF(percentage), TorF(delayfill), TorF(roundpositions))
        instr_pandl = self.parent.calc_or_cache(
            itemname, instrument_code, _pandl_for_instrument, self, percentage, delayfill, roundpositions)

        return instr_pandl

    def pandl_for_instrument_rules(self, instrument_code, delayfill=True):
        """
        Get the p&l for one instrument over multiple forecasts; as % of arbitrary capital
        
        All forecasting rules will have same expected std dev of returns; these aren't weighted
        
        KEY OUTPUT

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
        >>> system.accounts.pandl_for_instrument_rules("EDOLLAR").get_stats("sharpe")
        {'ewmac16': 0.6714147968308808, 'ewmac8': 0.681350200882741}
        """
        def _pandl_for_instrument_rules(
                system, instrument_code,  this_stage, delayfill):

            this_stage.log.terse("Calculating pandl for instrument rules for %s" % instrument_code,
                                 instrument_code=instrument_code)
            
            forecast_rules=system.combForecast.get_trading_rule_list(instrument_code
                                                                     )
            pandl_rules=[this_stage.pandl_for_instrument_forecast(
                                            instrument_code, rule_variation_name, delayfill)
                              for rule_variation_name in forecast_rules   
                            ]
            
            pandl_rules = accountCurveGroup(pandl_rules, forecast_rules)
            
            return pandl_rules

        itemname = "pandl_for_instrument__rules_delayfill%s" % TorF(
            delayfill)

        pandl_rules = self.parent.calc_or_cache(
            itemname, instrument_code, 
            _pandl_for_instrument_rules, self, delayfill)

        return pandl_rules


    def pandl_for_instrument_forecast(
            self, instrument_code, rule_variation_name, delayfill=True):
        """
        Get the p&l for one instrument and forecast; as % of arbitrary capital

        KEY OUTPUT:

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
        0.20644187486463425

        """
        def _pandl_for_instrument_forecast(
                system, instrument_code, rule_variation_name, this_stage, delayfill):

            this_stage.log.msg("Calculating pandl for instrument forecast for %s %s" % (instrument_code, rule_variation_name),
                               instrument_code=instrument_code, rule_variation_name=rule_variation_name)

            price = this_stage.get_daily_price(instrument_code)
            forecast = this_stage.get_capped_forecast(
                instrument_code, rule_variation_name)
            get_daily_returns_volatility = this_stage.get_daily_returns_volatility(
                instrument_code)

            ## FIX ME place holder
            SR_cost=0.0

            pandl_fcast = accountCurve(price, forecast=forecast, delayfill=delayfill, 
                                       roundpositions=False,
                                value_of_price_point=1.0, capital=None,
                                percentage=True, SR_cost=SR_cost, cost_per_block=None,
                                get_daily_returns_volatility=get_daily_returns_volatility)

            return pandl_fcast

        itemname = "pandl_for_instrument__forecast_delayfill%s" % TorF(
            delayfill)

        pandl_fcast = self.parent.calc_or_cache_nested(
            itemname, instrument_code, rule_variation_name,
            _pandl_for_instrument_forecast, self, delayfill)

        return pandl_fcast

    def portfolio(self, percentage=True, delayfill=True, roundpositions=False):
        """
        Get the p&l for entire portfolio

        :param percentage: Return results as % of total notional capital
        :type percentage: bool

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
        >>> system.accounts.portfolio(percentage=True).ann_std()
        0.2783243050399967
        """
        def _portfolio(system, not_used, this_stage,
                       percentage, delayfill, roundpositions):

            this_stage.log.terse("Calculating pandl for portfolio")

            instruments = this_stage.get_instrument_list()
            port_pandl = [
                this_stage.pandl_for_instrument(
                    instrument_code,
                    percentage=percentage,
                    delayfill=delayfill,
                    roundpositions=roundpositions) for instrument_code in instruments]
            
            port_pandl = accountCurveGroup(port_pandl, instruments)

            return port_pandl

        itemname = "portfolio__percentage%sdelayfill%sroundpositions%s" % (
            TorF(percentage), TorF(delayfill), TorF(roundpositions))

        port_pandl = self.parent.calc_or_cache(
            itemname, ALL_KEYNAME, _portfolio, self, percentage, delayfill,
            roundpositions)

        return port_pandl

    """
    ## More unused stuff, also commented out here
    def rules(self, subset=None, percentage=True, isolated=False, sumup=False):
        pass

    def rulegroup(self, subset=None, percentage=True, isolated=False, sumup=False):
        pass

    def rulestyle(self, subset=None, percentage=True, isolated=False, sumup=False):
        pass

    ## these should be in a futures accounting object...

    def assetclass(self, subset=None, percentage=True, isolated=False, sumup=False):
        pass

    def country(self, subset=None, percentage=True, isolated=False, sumup=False):
        pass
    """


if __name__ == '__main__':
    import doctest
    doctest.testmod()
