import pandas as pd
import numpy as np

from syscore.accounting import accountCurve, accountCurveGroup, weighted
from systems.stage import SystemStage
from systems.basesystem import ALL_KEYNAME
from systems.defaults import system_defaults
from syscore.algos import robust_vol_calc, apply_buffer
from syscore.genutils import TorF
from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.pdutils import  turnover
from dis import Instruction

ARBITRARY_FORECAST_CAPITAL=100.0

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

        system.data.get_value_of_block_price_move
            found in self.get_value_of_price_move()

        system.rawdata.daily_returns_volatility() or system.data.daily_prices(instrument_code)
            found in self.get_daily_returns_volatility()
            
        system.portfolio.get_buffers_for_position(instrument_code)
            found in self.get_buffers_for_position

        system.portfolio.get_instrument_diversification_multiplier
            found in self.portfolio.get_instrument_diversification_multiplier
            
        system.portfolio.get_instrument_weights
            found in self.get_instrument_weights()

        system.combForecast.get_trading_rule_list
            found in self.get_trading_rule_list

        system.combForecast.has_same_rules_as_code
            found in self.has_same_rules_as_code

    KEY OUTPUTS: Used for optimisation:
                 system.accounts.pandl_for_instrument_rules_unweighted
                 system.accounts.accounts.pandl_across_subsystems

    NOTE - there are many unused methods in this function - reserved for future use

    Name: accounts
    """

    def __init__(self):
        """
        Create a SystemStage for accounting



        """
        setattr(self, "name", "accounts")
        setattr(self, "description", "Account()")

        protected = []
        setattr(self, "_protected", protected)

        nopickle=["portfolio",  "pandl_for_instrument_forecast",
                  "pandl_for_subsystem", "pandl_across_subsystems", "pandl_for_instrument",
                  "pandl_for_instrument_rules_unweighted", 'pandl_for_trading_rule_unweighted',
                  'pandl_for_trading_rule','pandl_for_instrument_rules', 'pandl_for_instrument_forecast'
                  ]

        setattr(self, "_nopickle", nopickle)




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
        def _get_aligned_forecast(system, instrument_code, rule_variation_name, this_stage):
            price=self.get_daily_price(instrument_code)
            forecast=self.get_capped_forecast(instrument_code, rule_variation_name)
            
            forecast=forecast.reindex(price.index).ffill()
            
            return forecast
        
        aligned_forecast = self.parent.calc_or_cache_nested(
            'get_aligned_forecast', instrument_code, rule_variation_name,
            _get_aligned_forecast, self)

        return aligned_forecast


    def has_same_rules_as_code(self, instrument_code):
        """
        Return instruments with same trading rules as this instrument
    
        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: list of str

        """
        return self.parent.combForecast.has_same_rules_as_code(instrument_code)



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

    def get_instrument_diversification_multiplier(self):
        """
        Get instrument div mult

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        """

        return self.parent.portfolio.get_instrument_diversification_multiplier()

    def get_forecast_diversification_multiplier(self, instrument_code):
        """
        Get the f.d.m from the previous module

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: dict of Tx1 pd.DataFrames

        """
        return self.parent.combForecast.get_forecast_diversification_multiplier(
            instrument_code)

    def get_instrument_weights(self):
        """
        Get instrument weights

        KEY INPUT

        :returns: Tx1 pd.DataFrame


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


    def get_aligned_subsystem_position(self, instrument_code):
        """
        Get the position assuming all capital in one instruments, aligned to price

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame


        """
        def _get_aligned_subsystem_position(system, instrument_code,  this_stage):
            price=this_stage.get_daily_price(instrument_code)
            sspos=this_stage.get_subsystem_position(instrument_code)
            
            sspos = sspos.reindex(price.index).ffill()
            
            return sspos
        
        aligned_subsys_pos= self.parent.calc_or_cache(
            'get_aligned_subsystem_position', instrument_code, 
            _get_aligned_subsystem_position, self)

        return aligned_subsys_pos


    def get_trading_rule_list(self, instrument_code):
        """
        Get the trading rules for this instrument, from a previous module

        KEY INPUT

        :returns: list of str

        """
        return self.parent.combForecast.get_trading_rule_list(instrument_code)

    def get_entire_trading_rule_list(self):
        """
        Get the trading rules for all instruments


        :returns: list of str

        """
        instrument_list=self.get_instrument_list()
        rules=[self.get_trading_rule_list(instrument_code) for instrument_code in instrument_list]
        rules=sum(rules, [])
        rules.sort()
        
        return list(set(rules))

    def get_instrument_list(self):
        """
        Get the trading rules for this instrument, from a previous module

        :returns: list of str

        KEY INPUT

        """
        return self.parent.get_instrument_list()


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

    def get_aligned_fx(self, instrument_code):
        
        def _get_aligned_fx(system, instrument_code,  this_stage):
            price=self.get_daily_price(instrument_code)
            fx=self.get_fx_rate(instrument_code)
            
            fx=fx.reindex(price.index).ffill()
            
            return fx
        
        aligned_fx = self.parent.calc_or_cache(
            'get_aligned_fx', instrument_code, 
            _get_aligned_fx, self)


        return aligned_fx

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


    def get_buffers_for_position(self, instrument_code):
        """
        Get the buffered position from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx2 pd.DataFrame: columns top_pos, bot_pos

        KEY INPUT
        """
        
        return self.parent.portfolio.get_buffers_for_position(instrument_code)

    def get_daily_price(self, instrument_code):
        """
        Get the instrument price from rawdata

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: Tx1 pd.DataFrames

        """
        def _get_daily_price(system, instrument_code, this_stage):
            return system.data.daily_prices(instrument_code)

        instrument_price = self.parent.calc_or_cache(
            'get_daily_price', instrument_code, _get_daily_price, self)

        return instrument_price

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

        def _get_value_of_price_move(system, instrument_code, this_stage):
            return  system.data.get_value_of_block_price_move(
                                                        instrument_code)

        value_of_price_move = self.parent.calc_or_cache(
            'get_value_of_price_move', instrument_code, _get_value_of_price_move, self)


        return value_of_price_move

    def get_raw_cost_data(self, instrument_code):
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
        def _get_raw_cost_data(system, instrument_code, this_stage):
            return system.data.get_raw_cost_data(instrument_code)

        raw_cost_data = self.parent.calc_or_cache(
            'get_raw_cost_data', instrument_code, _get_raw_cost_data, self)
        
        return raw_cost_data

    def get_daily_returns_volatility(self, instrument_code):
        """
        Get the daily return (not %) volatility from previous stage, or calculate

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: Tx1 pd.DataFrames

        """


        def _get_daily_returns_volatility(system, instrument_code, this_stage):
            if hasattr(system, "rawdata"):
                returns_vol = system.rawdata.daily_returns_volatility(
                    instrument_code)
            else:
                price = self.get_daily_price(instrument_code)
                returns_vol = robust_vol_calc(price.diff())

            return returns_vol

        price_volatility = self.parent.calc_or_cache(
            'get_daily_returns_volatility', instrument_code, _get_daily_returns_volatility, self)

        return price_volatility

    def get_volatility_scalar(self, instrument_code):
        """
        Get the volatility scalar
        
        KEY INPUT
        
        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame
        
        """
        
        return self.parent.positionSize.get_volatility_scalar(instrument_code)
    
    def get_aligned_volatility_scalar(self, instrument_code):
        """
        Get the volatility scalar aligned to price
        
        KEY INPUT
        
        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame
        
        """
        
        def _get_aligned_vol_scalar(system, instrument_code,  this_stage):
            price=this_stage.get_daily_price(instrument_code)
            vs=this_stage.get_volatility_scalar(instrument_code)
            
            vs = vs.reindex(price.index).ffill()
            
            return vs
        
        aligned_vs= self.parent.calc_or_cache(
            'get_aligned_vol_scalar', instrument_code, 
            _get_aligned_vol_scalar, self)

        return aligned_vs

    
    
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

        inst_weight_this_code = instr_weights[
            instrument_code]

        multiplier = inst_weight_this_code * idm
        
        price = self.get_daily_price(instrument_code)
        
        return multiplier.reindex(price.index).ffill()
    
    def get_forecast_scaling_factor(self, instrument_code, rule_variation_name):
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
            
            fcast_weight_this_code = forecast_weights[
                rule_variation_name]
        else:
            fcast_weight_this_code = self.get_aligned_forecast(instrument_code, rule_variation_name)
            fcast_weight_this_code[:]=0.0

        multiplier = fcast_weight_this_code* fdm

        return multiplier


    def get_instrument_forecast_scaling_factor(self, instrument_code, rule_variation_name):
        """
        Get forecast weight * FDM  *instrument_weight * IDM
        
        :param instrument_code: instrument to value for
        :type instrument_code: str

        :param rule_variation_name: trading rule
        :type rule_variation_name: str

        :returns: Tx1 pd.DataFrame
        
        """
        
        fsf=self.get_forecast_scaling_factor(instrument_code, rule_variation_name)
        isf=self.get_instrument_scaling_factor(instrument_code)

        (fsf, isf)= fsf.align(isf, join="inner")
        
        return fsf*isf
    
    def get_capital_in_rule(self, rule_variation_name):
        """
        Get sum of forecast weight * FDM  *instrument_weight * IDM for a given rule
        
        :param rule_variation_name: trading rule
        :type rule_variation_name: str

        :returns: Tx1 pd.DataFrame
        
        """
    
        instrument_list = self.get_instrument_list()
        all_risk_allocations = [self.get_instrument_forecast_scaling_factor(instrument_code, rule_variation_name) for 
                                instrument_code in instrument_list]
        all_risk_allocations=pd.concat(all_risk_allocations, axis=1)
        
        return all_risk_allocations.sum(axis=1)
        
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

        def _get_SR_cost(
                system, instrument_code, this_stage):
            
            
            raw_costs=this_stage.get_raw_cost_data(instrument_code)
            block_value=this_stage.get_value_of_price_move(instrument_code)

            price_slippage=raw_costs['price_slippage']
            value_of_block_commission=raw_costs['value_of_block_commission']
            percentage_cost=raw_costs['percentage_cost']
            value_of_pertrade_commission=raw_costs['value_of_pertrade_commission']
            
            
            daily_vol=this_stage.get_daily_returns_volatility(instrument_code)
            daily_price=this_stage.get_daily_price(instrument_code)

            last_date=daily_price.index[-1]
            start_date=last_date-pd.DateOffset(years=1)
            average_price=float(daily_price[start_date:].mean())
            average_vol=float(daily_vol[start_date:].mean())
        
            ## Cost in Sharpe Ratio terms
            ## First work out costs in price terms
            price_block_commission=value_of_block_commission/block_value
            price_percentage_cost=average_price*percentage_cost
            price_per_trade_cost=value_of_pertrade_commission/block_value ## assume one trade per contract

            price_total=price_slippage+price_block_commission+price_percentage_cost+price_per_trade_cost
            
            avg_annual_vol = average_vol * ROOT_BDAYS_INYEAR
            
            SR_cost = 2.0 * price_total / ( avg_annual_vol )
            

            return SR_cost
            
        SR_cost = self.parent.calc_or_cache(
            "get_SR_cost", instrument_code, _get_SR_cost, self)

        return SR_cost
    

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

        def _get_cash_costs(
                system, instrument_code, this_stage):
            
            
            raw_costs=this_stage.get_raw_cost_data(instrument_code)
            block_value=this_stage.get_value_of_price_move(instrument_code)

            price_slippage=raw_costs['price_slippage']
            value_of_block_commission=raw_costs['value_of_block_commission']
            percentage_cost=raw_costs['percentage_cost']
            value_of_pertrade_commission=raw_costs['value_of_pertrade_commission']
            
            ## Cost in actual terms in local currency
            value_of_slippage=price_slippage*block_value
            value_total_per_block=value_of_block_commission+value_of_slippage
            
            cash_costs=(value_total_per_block, value_of_pertrade_commission, percentage_cost)

            return cash_costs

        cash_costs = self.parent.calc_or_cache(
            "get_cash_costs", instrument_code, _get_cash_costs, self)

        return cash_costs

    def get_costs(self, instrument_code):
        """
        Get the relevant kinds of cost for an instrument
        
        :param instrument_code: instrument to value for
        :type instrument_code: str

        :returns: 2 tuple
        """
        
        use_SR_costs=bool(self.parent.config.use_SR_costs)
        
        if use_SR_costs:
            return (self.get_SR_cost(instrument_code), None)
        else:
            return (None, self.get_cash_costs(instrument_code))
        
    def subsystem_turnover(self, instrument_code, roundpositions):
        """
        Get the annualised turnover for an instrument subsystem

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: float


        """
        def _subsystem_turnover(
                system, instrument_code,  this_stage, roundpositions):

            positions = this_stage.get_aligned_subsystem_position(instrument_code)
            average_position_for_turnover=this_stage.get_aligned_volatility_scalar(instrument_code)
            
            return turnover(positions, average_position_for_turnover)

        subsys_turnover = self.parent.calc_or_cache(
            "subsystem_turnover", instrument_code,
            _subsystem_turnover, self, roundpositions, flags="%s" % TorF(roundpositions))

        return subsys_turnover

    def subsystem_SR_costs(self, instrument_code, roundpositions=False):
        """
        Get the annualised SR costs for an instrument subsystem

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: float
        
        KEY OUTPUT (used for portfolio optimisation)
        
        

        """
        def _subsystem_SR_costs(
                system, instrument_code,  this_stage, roundpositions):
            
            SR_cost_per_turnover=this_stage.get_SR_cost(instrument_code)
                
            turnover_for_SR = this_stage.subsystem_turnover(instrument_code, roundpositions = roundpositions)
            SR_cost = SR_cost_per_turnover * turnover_for_SR
            
            return SR_cost

        subsystem_SR_costs = self.parent.calc_or_cache(
            "subsystem_SR_costs", instrument_code,
            _subsystem_SR_costs, self, roundpositions, flags="%s" % TorF(roundpositions))

        return subsystem_SR_costs
        

    def pandl_for_subsystem(

            self, instrument_code,  delayfill=True, roundpositions=False):
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

        def _pandl_for_subsystem(
                system, instrument_code, this_stage, delayfill, roundpositions):

            this_stage.log.msg("Calculating pandl for subsystem for instrument %s" % instrument_code,
                               instrument_code=instrument_code)

            
            price = this_stage.get_daily_price(instrument_code)
            positions = this_stage.get_aligned_subsystem_position(instrument_code)

            fx = this_stage.get_aligned_fx(instrument_code)
            value_of_price_point = this_stage.get_value_of_price_move(
                instrument_code)
            get_daily_returns_volatility = this_stage.get_daily_returns_volatility(
                instrument_code)


            (SR_cost_per_turnover, cash_costs)=this_stage.get_costs(instrument_code)
            
            if SR_cost_per_turnover is not None:
                SR_cost = self.subsystem_SR_costs(instrument_code, roundpositions)
                
            capital = this_stage.get_notional_capital()
            ann_risk_target = this_stage.get_ann_risk_target()

            instr_pandl = accountCurve(price, positions = positions,
                                       delayfill = delayfill, roundpositions = roundpositions, 
                                fx=fx, value_of_price_point=value_of_price_point, capital=capital,
                                 SR_cost=SR_cost,  cash_costs = cash_costs,
                                get_daily_returns_volatility=get_daily_returns_volatility,
                                ann_risk_target = ann_risk_target)

            return instr_pandl

        instr_pandl = self.parent.calc_or_cache(
            "pandl_for_subsystem", instrument_code, _pandl_for_subsystem, 
            self,  delayfill, roundpositions,
            flags="__delayfill%sroundpositions%s" % (
             TorF(delayfill), TorF(roundpositions)))

        return instr_pandl


    def pandl_across_subsystems(
                                self,  delayfill=True, roundpositions=False):
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
        def _pandl_across_subsystems(
                system, instrumentCodeNotUsed, this_stage,  delayfill, roundpositions):

            ## Subsystems use entire capital
            capital = this_stage.get_notional_capital()
            
            instruments = this_stage.get_instrument_list()
            pandl_across_subsys = [
                this_stage.pandl_for_subsystem(
                    instrument_code,
                    delayfill=delayfill,
                    roundpositions=roundpositions) for instrument_code in instruments]
            
            pandl = accountCurveGroup(pandl_across_subsys, instruments, 
                                      capital=capital,
                                      weighted_flag=False)
            
            return pandl

        instr_pandl = self.parent.calc_or_cache(
            "pandl_across_subsystems", ALL_KEYNAME, _pandl_across_subsystems, self, 
             delayfill, roundpositions,
                    flags = "delayfill%sroundpositions%s" % (
             TorF(delayfill), TorF(roundpositions)))

        return instr_pandl


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

        def _get_buffered_position(
                system, instrument_code, this_stage,  roundpositions):

            this_stage.log.msg("Calculating buffered positions")
            optimal_position=this_stage.get_notional_position(instrument_code)
            pos_buffers=this_stage.get_buffers_for_position(instrument_code)
            trade_to_edge=system.config.buffer_trade_to_edge
    
            buffered_position = apply_buffer(optimal_position, pos_buffers, 
                                             trade_to_edge=trade_to_edge, roundpositions=roundpositions)
            
            buffered_position.columns=["position"]
            
            return buffered_position

        buffered_position = self.parent.calc_or_cache(
            "get_buffered_position", instrument_code, _get_buffered_position, self, 
            roundpositions,
            flags="roundpositions%s" %  TorF(roundpositions))

        return buffered_position

    def instrument_turnover(self, instrument_code, roundpositions=True):
        """
        Get the annualised turnover for an instrument

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float


        """
        def _instrument_turnover(
                system, instrument_code,  this_stage, roundpositions):

            average_position_for_turnover=this_stage.get_aligned_volatility_scalar(instrument_code)  *  this_stage.get_instrument_scaling_factor(instrument_code)
            
            positions = this_stage.get_buffered_position(instrument_code, roundpositions = roundpositions)
            
            return turnover(positions, average_position_for_turnover)

        instr_turnover = self.parent.calc_or_cache(
            "instrument_turnover", instrument_code,
            _instrument_turnover, self, roundpositions,
            flags="%s" % TorF(roundpositions))

        return instr_turnover

    def pandl_for_instrument(
            self, instrument_code,  delayfill=True, roundpositions=True):
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

        def _pandl_for_instrument(
                system, instrument_code, this_stage,  delayfill, roundpositions):

            this_stage.log.msg("Calculating pandl for instrument for %s" % instrument_code,
                               instrument_code=instrument_code)

            price = this_stage.get_daily_price(instrument_code)
            positions = this_stage.get_buffered_position(instrument_code, roundpositions = roundpositions)
            fx = this_stage.get_aligned_fx(instrument_code)
            value_of_price_point = this_stage.get_value_of_price_move(
                instrument_code)
            get_daily_returns_volatility = this_stage.get_daily_returns_volatility(
                instrument_code)


            capital = this_stage.get_notional_capital()
            ann_risk_target = this_stage.get_ann_risk_target()

            (SR_cost, cash_costs)=this_stage.get_costs(instrument_code)
            

            instr_pandl = accountCurve(price, positions = positions,
                                       delayfill = delayfill, roundpositions = roundpositions, 
                                fx=fx, value_of_price_point=value_of_price_point, capital=capital,
                                ann_risk_target = ann_risk_target,
                                 SR_cost=SR_cost, cash_costs = cash_costs,
                                get_daily_returns_volatility=get_daily_returns_volatility)

            if SR_cost is not None:
                ## Note that SR cost is done as a proportion of capital
                ## Since we're only using part of the capital we need to correct for this
                turnover_for_SR=this_stage.instrument_turnover(instrument_code, roundpositions = roundpositions)
                SR_cost = SR_cost * turnover_for_SR
                weighting = this_stage.get_instrument_scaling_factor(instrument_code)
                apply_weight_to_costs_only=True
                
                instr_pandl=weighted(instr_pandl, 
                                 weighting = weighting,
                                apply_weight_to_costs_only=apply_weight_to_costs_only)
                
            else:
                ## Costs wil be correct
                ## We don't need to do anything
                pass
                

            return instr_pandl

        instr_pandl = self.parent.calc_or_cache(
            "pandl_for_instrument", instrument_code, _pandl_for_instrument, self, 
             delayfill, roundpositions,
            flags="delayfill%sroundpositions%s" % (
             TorF(delayfill), TorF(roundpositions)))

        return instr_pandl

    def pandl_for_trading_rule(self, rule_variation_name, delayfill=True):
        """
        Get the p&l for one trading rule over multiple instruments; as % of it's risk contribution

        Within the trading rule the instrument returns are weighted by instrument weight
        
        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurve

        """
        def _pandl_for_trading_rule(
                system, instrument_code_unused,  rule_variation_name, this_stage,  delayfill):

            this_stage.log.terse("Calculating pandl for trading rule %s" % rule_variation_name)
            
            this_stage.log.terse("Calculating pandl for trading rule %s" % rule_variation_name)
            
            instrument_list=system.get_instrument_list()
            instrument_list=[instr_code for instr_code in instrument_list 
                             if rule_variation_name in this_stage.get_trading_rule_list(instr_code)]
            
            ## already weighted
            ## capital on these will be the default
            pandl_by_instrument_weighted=[this_stage.pandl_for_instrument_forecast_weighted(
                                            instr_code, rule_variation_name, delayfill)
                              for instr_code in instrument_list   
                            ]
            
            ## now we weight so total capital is correct
            capital_this_rule=this_stage.get_capital_in_rule(rule_variation_name)
            
            
            def _cleanweightelement( capelement):
                if np.isnan(capelement):
                    return 0.0
                if capelement==0.0:
                    return 0.0
                else:
                    return 1.0/capelement

            weight=[_cleanweightelement(capelement) for capelement in list(capital_this_rule.values)]
            weight=pd.Series(weight, index=capital_this_rule.index)
            
            pandl_by_instrument_reweighted=[weighted(pandl_for_instrument, weight,
                                                     allow_reweighting=True) for 
                                             pandl_for_instrument in pandl_by_instrument_weighted]

            pandl_rule = accountCurveGroup(pandl_by_instrument_reweighted, instrument_list, 
                                           capital=ARBITRARY_FORECAST_CAPITAL,
                                           weighted_flag=True)
            
            return pandl_rule


        pandl_trading_rule = self.parent.calc_or_cache_nested(
            "pandl_for_trading_rule", ALL_KEYNAME, rule_variation_name, 
            _pandl_for_trading_rule, self, delayfill,
            flags = "delayfill%s" % TorF(delayfill))

        return pandl_trading_rule

    def pandl_for_trading_rule_weighted(self, rule_variation_name, delayfill=True):
        """
        Get the p&l for one trading rule over multiple instruments; as % of total capital

        Within the trading rule the instrument returns are weighted by risk contribution
        
        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurveGroup

        """
        def _pandl_for_trading_rule_weighted(
                system, instrument_code_unused,  rule_variation_name, this_stage,  delayfill):

            this_stage.log.terse("Calculating pandl for trading rule %s" % rule_variation_name)
            
            instrument_list=system.get_instrument_list()
            instrument_list=[instr_code for instr_code in instrument_list 
                             if rule_variation_name in this_stage.get_trading_rule_list(instr_code)]
            
            ## already weighted, don't need to do again
            pandl_by_instrument_weighted=[this_stage.pandl_for_instrument_forecast_weighted(
                                            instr_code, rule_variation_name, delayfill)
                              for instr_code in instrument_list   
                            ]

            pandl_rule = accountCurveGroup(pandl_by_instrument_weighted, instrument_list, 
                                           capital= ARBITRARY_FORECAST_CAPITAL, 
                                           weighted_flag=True)
            
            return pandl_rule


        pandl_trading_rule_weighted = self.parent.calc_or_cache_nested(
            "pandl_for_trading_rule_weighted", ALL_KEYNAME, rule_variation_name, 
            _pandl_for_trading_rule_weighted, self, delayfill,
            flags = "delayfill%s" % TorF(delayfill))

        return pandl_trading_rule_weighted



    def pandl_for_trading_rule_unweighted(self, rule_variation_name, delayfill=True):
        """
        Get the p&l for one trading rule over multiple instruments; as % of arbitrary capital

        Within the trading rule the instrument returns are NOT weighted by instrument weight
        
        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurve

        """
        def _pandl_for_trading_rule_unweighted(
                system, instrument_code_unused,  rule_variation_name, this_stage,  delayfill):

            this_stage.log.terse("Calculating pandl for trading rule (unweighted) %s" % rule_variation_name)
            
            instrument_list=system.get_instrument_list()
            instrument_list=[instr_code for instr_code in instrument_list 
                             if rule_variation_name in this_stage.get_trading_rule_list(instr_code)]
            
            pandl_by_instrument=[this_stage.pandl_for_instrument_forecast(
                                            instr_code, rule_variation_name, delayfill)
                              for instr_code in instrument_list   
                            ]
            
            pandl_rule = accountCurveGroup(pandl_by_instrument, instrument_list, 
                                           capital= ARBITRARY_FORECAST_CAPITAL, weighted_flag=False)
            
            return pandl_rule

        pandl_trading_rule_unweighted = self.parent.calc_or_cache_nested(
            "pandl_for_trading_rule_unweighted", ALL_KEYNAME, rule_variation_name, 
            _pandl_for_trading_rule_unweighted, self, delayfill,
            flags = "delayfill%s" % TorF(delayfill))

        return pandl_trading_rule_unweighted


    def pandl_for_instrument_rules_unweighted(self, instrument_code, rule_list=None, delayfill=True):
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
        def _pandl_for_instrument_rules_unweighted(
                system, instrument_code,  this_stage, delayfill, rule_list):

            this_stage.log.terse("Calculating pandl for instrument rules for %s" % instrument_code,
                                 instrument_code=instrument_code)
            
            if rule_list is None:
                rule_list=this_stage.get_trading_rule_list(instrument_code
                                                                     )
            pandl_rules=[this_stage.pandl_for_instrument_forecast(
                                            instrument_code, rule_variation_name, delayfill = delayfill)
                              for rule_variation_name in rule_list   
                            ]
            
            
            pandl_rules = accountCurveGroup(pandl_rules, rule_list, capital=ARBRITARY_FORECAST_CAPITAL,
                                             weighted_flag=False)
            
            return pandl_rules

        pandl_rules = self.parent.calc_or_cache(
            "pandl_for_instrument_rules_unweighted", instrument_code, 
            _pandl_for_instrument_rules_unweighted, self, delayfill, rule_list, 
            flags="_delayfill%s" % TorF(
            delayfill))

        return pandl_rules

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
        def _pandl_for_instrument_rules(
                system, instrument_code,  this_stage, delayfill):

            this_stage.log.terse("Calculating pandl for instrument rules for %s" % instrument_code,
                                 instrument_code=instrument_code)
            
            forecast_rules=this_stage.get_trading_rule_list(instrument_code
                                                                     )
            pandl_rules_unweighted=[this_stage.pandl_for_instrument_forecast(
                                            instrument_code, rule_variation_name, delayfill = delayfill)
                              for rule_variation_name in forecast_rules   
                            ]

            pandl_rules=[weighted(
                         pandl_this_rule,
                         weighting = this_stage.get_forecast_scaling_factor(instrument_code, rule_variation_name))
                              for (pandl_this_rule, rule_variation_name) in zip(
                                                                                pandl_rules_unweighted,
                                                                                forecast_rules)   
                            ]
            
            
            pandl_rules = accountCurveGroup(pandl_rules, forecast_rules, 
                                            capital=ARBITRARY_FORECAST_CAPITAL,
                                            weighted_flag=True)
            
            return pandl_rules


        pandl_rules = self.parent.calc_or_cache(
            "pandl_for_instrument_rules", instrument_code, 
            _pandl_for_instrument_rules, self, delayfill,
            flags="delayfill%s" % TorF(
            delayfill))

        return pandl_rules


    def forecast_turnover_for_list(self, instrument_code_list, rule_variation_name):
        """
        Get the average turnover for a rule, over instrument_code_list

        :param instrument_code_list: instruments to get values for
        :type instrument_code_list: list of str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float
        
        """

        def _forecast_turnover_for_list(
                system, NOTUSEDinstrument_code_ref, rule_variation_name, this_stage,
                instrument_code_list):

            average_forecast_for_turnover=system_defaults['average_absolute_forecast']

            forecast_list=[this_stage.get_capped_forecast(
                instrument_code, rule_variation_name)
                        for instrument_code in instrument_code_list]
            
            turnovers=[turnover(forecast, average_forecast_for_turnover) for forecast in forecast_list]

            if len(instrument_code_list)==1:
                return turnovers[0]
            
            ## weight by length
            forecast_lengths=[len(forecast.index) for forecast in forecast_list]
            total_length=sum(forecast_lengths)
            weighted_turnovers=[tover*fc_length/total_length for (tover, fc_length) in zip(turnovers, forecast_lengths)]
            
            avg_turnover = sum(weighted_turnovers)
            
            return avg_turnover

        ## 
        instrument_code_ref = "_".join(instrument_code_list) 
        
        fcast_turnover = self.parent.calc_or_cache_nested(
            "forecast_turnover_for_list", instrument_code_ref, rule_variation_name,
            _forecast_turnover_for_list, self, instrument_code_list)

        return fcast_turnover
        

    def forecast_turnover(self, instrument_code, rule_variation_name):
        """
        Get the annualised turnover for a forecast/rule combination

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float


        """
        def _forecast_turnover(
                system, instrument_code, rule_variation_name, this_stage, use_pooled_turnover):
            
            if use_pooled_turnover:
                instrument_code_list = this_stage.has_same_rules_as_code(instrument_code)
            else:
                instrument_code_list = [instrument_code]

            turnover_for_SR=this_stage.forecast_turnover_for_list(instrument_code_list, rule_variation_name)
            
            return turnover_for_SR

        use_pooled_turnover = self.parent.config.forecast_cost_estimates['use_pooled_turnover']
        
        fcast_turnover = self.parent.calc_or_cache_nested(
            "forecast_turnover", instrument_code, rule_variation_name,
            _forecast_turnover, self, use_pooled_turnover)

        return fcast_turnover

    def get_SR_cost_instr_forecast_for_list(self, instrument_code_list, rule_variation_name):
        """
        Get the SR cost for a forecast/rule combination, averaged across multiple instruments

        :param instrument_code_list: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float


        """

        def _get_SR_cost_instr_forecast_for_list(
                system, NOTUSEDinstrument_code_ref, rule_variation_name, this_stage,
                instrument_code_list):
            
            turnover_list=[this_stage.forecast_turnover(instrument_code, rule_variation_name)
                        for instrument_code in instrument_code_list]
            
            SR_cost_per_turnover=[this_stage.get_SR_cost(instrument_code) for instrument_code in instrument_code_list]

            forecast_list=[this_stage.get_capped_forecast(
                instrument_code, rule_variation_name)
                        for instrument_code in instrument_code_list]

            SR_cost = [tover * SRcpt for (tover, SRcpt) in zip(turnover_list, SR_cost_per_turnover)]
            
            ## weight by length
            forecast_lengths=[len(forecast.index) for forecast in forecast_list]
            total_length=sum(forecast_lengths)
            weighted_SR_costs=[SRc*fc_length/total_length for (SRc, fc_length) in zip(SR_cost, forecast_lengths)]
            
            avg_SR_cost = sum(weighted_SR_costs)
            
            return avg_SR_cost
            
        instrument_code_ref = "_".join(instrument_code_list) 

        SR_cost_for_instr_fcast_list = self.parent.calc_or_cache_nested(
            "get_SR_cost_instr_forecast_for_list", instrument_code_ref, rule_variation_name,
            _get_SR_cost_instr_forecast_for_list, self, instrument_code_list)

        return SR_cost_for_instr_fcast_list
        





    def get_SR_cost_for_instrument_forecast(self, instrument_code, rule_variation_name):
        """
        Get the SR cost for a forecast/rule combination

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param rule_variation_name: rule to get values for
        :type rule_variation_name: str

        :returns: float

        KEY OUTPUT
        """

        def _get_SR_cost_for_instrument_forecast(
                system, instrument_code, rule_variation_name, this_stage, use_pooled_costs):
            
            if use_pooled_costs:
                instrument_code_list = this_stage.has_same_rules_as_code(instrument_code)
                SR_cost=this_stage.get_SR_cost_instr_forecast_for_list(instrument_code_list, rule_variation_name)

            else:
                ## note the turnover may still be pooled..
                SR_cost = this_stage.forecast_turnover(instrument_code, rule_variation_name)*this_stage.get_SR_cost(instrument_code)
            
            return SR_cost

        use_pooled_costs = self.parent.config.forecast_cost_estimates['use_pooled_costs']
        
        SR_cost_for_instr_fcast = self.parent.calc_or_cache_nested(
            "SR_cost_for_instrument_forecast", instrument_code, rule_variation_name,
            _get_SR_cost_for_instrument_forecast, self, use_pooled_costs)

        return SR_cost_for_instr_fcast
        


    def pandl_for_instrument_forecast_weighted(
            self, instrument_code, rule_variation_name, delayfill=True):
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
        
        def _pandl_for_instrument_forecast_weighted(system, instrument_code, 
                                           rule_variation_name, this_stage, delayfill):
                    
            this_stage.log.msg("Calculating pandl for instrument forecast weighted for %s %s" % (instrument_code, rule_variation_name),
                               instrument_code=instrument_code, rule_variation_name=rule_variation_name)

            pandl = this_stage.pandl_for_instrument_forecast(instrument_code, rule_variation_name, delayfill=delayfill)    
            weight = this_stage.get_instrument_forecast_scaling_factor( instrument_code, rule_variation_name)            
            pandl = weighted(pandl, weight)

            return pandl
        
        pandl_fcast = self.parent.calc_or_cache_nested(
            "pandl_for_instrument_forecast_weighted", instrument_code, rule_variation_name,
            _pandl_for_instrument_forecast_weighted, self, delayfill,
            flags="delayfill%s" %   TorF(delayfill))


        return pandl_fcast


    def pandl_for_instrument_forecast(
            self, instrument_code, rule_variation_name, delayfill=True):
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
        
        def _pandl_for_instrument_forecast(system, instrument_code, 
                                           rule_variation_name, this_stage, delayfill):
                    
            this_stage.log.msg("Calculating pandl for instrument forecast for %s %s" % (instrument_code, rule_variation_name),
                               instrument_code=instrument_code, rule_variation_name=rule_variation_name)
    
            ## by construction all these things are aligned
            price = this_stage.get_daily_price(instrument_code)
            forecast = this_stage.get_aligned_forecast(
                instrument_code, rule_variation_name)
            get_daily_returns_volatility = this_stage.get_daily_returns_volatility(
                instrument_code)
    
            ## We NEVER use cash costs for forecasts ...
            SR_cost = this_stage.get_SR_cost_for_instrument_forecast(instrument_code, rule_variation_name)
                        
            ## We use percentage returns (as no 'capital') and don't round positions
            pandl_fcast = accountCurve(price, forecast=forecast, delayfill=delayfill, 
                                       roundpositions=False,
                                value_of_price_point=1.0, capital=ARBITRARY_FORECAST_CAPITAL,
                                SR_cost=SR_cost, cash_costs=None,
                                get_daily_returns_volatility=get_daily_returns_volatility)
            
            return pandl_fcast
        
        pandl_fcast = self.parent.calc_or_cache_nested(
            "pandl_for_instrument_forecast", instrument_code, rule_variation_name,
            _pandl_for_instrument_forecast, self, delayfill,
            flags="delayfill%s" %   TorF(delayfill))


        return pandl_fcast

    def pandl_for_all_trading_rules(self, delayfill=True):
        """
        Get the p&l for all trading rules; as % of total capital

        Each trading rule is weighted as a proportion of total capital
        
        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurveGroup

        """
        def _pandl_for_all_trading_rules(
                system, instrument_code_unused,   this_stage,  delayfill):

            this_stage.log.terse("Calculating pandl for all trading rules")

            variations=this_stage.get_entire_trading_rule_list()            
            
            ## already weighted, don't need to do again
            pandl_by_trading_rule_weighted=[this_stage.pandl_for_trading_rule_weighted(rulename, delayfill)
                                            for rulename in variations]

            ## this is a group of groups... will it work?
            pandl_all_rules = accountCurveGroup(pandl_by_trading_rule_weighted, variations, 
                                                capital = ARBITRARY_FORECAST_CAPITAL,
                                                weighted_flag=True)
            
            return pandl_all_rules


        pandl_for_all_trading_rules = self.parent.calc_or_cache(
            "pandl_for_all_trading_rules", ALL_KEYNAME,  
            _pandl_for_all_trading_rules, self, delayfill,
            flags = "delayfill%s" % TorF(delayfill))

        return pandl_for_all_trading_rules

    def pandl_for_all_trading_rules_unweighted(self, delayfill=True):
        """
        Get the p&l for all trading rules; unweighted

        Each trading rule has capital in isolation
        
        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :returns: accountCurveGroup

        """
        def _pandl_for_all_trading_rules_unweighted(
                system, instrument_code_unused,   this_stage,  delayfill):

            this_stage.log.terse("Calculating pandl for all trading rules unweighted")

            variations=this_stage.get_entire_trading_rule_list()            
            
            ## already weighted, don't need to do again
            pandl_by_trading_rule_unweighted=[this_stage.pandl_for_trading_rule(rulename, delayfill)
                                            for rulename in variations]

            ## this is a group of groups... will it work?
            pandl_all_rules = accountCurveGroup(pandl_by_trading_rule_unweighted, variations, 
                                                capital=ARBITRARY_FORECAST_CAPITAL,
                                                weighted_flag=False)
            
            return pandl_all_rules


        pandl_for_all_trading_rules_unweighted = self.parent.calc_or_cache(
            "pandl_for_all_trading_rules_unweighted", ALL_KEYNAME,  
            _pandl_for_all_trading_rules_unweighted, self, delayfill,
            flags = "delayfill%s" % TorF(delayfill))

        return pandl_for_all_trading_rules_unweighted


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
        def _portfolio(system, not_used, this_stage,
                        delayfill, roundpositions):

            this_stage.log.terse("Calculating pandl for portfolio")
            capital=this_stage.get_notional_capital()
            instruments = this_stage.get_instrument_list()
            port_pandl = [
                this_stage.pandl_for_instrument(
                    instrument_code,
                    delayfill=delayfill,
                    roundpositions=roundpositions) for instrument_code in instruments]
            
            port_pandl = accountCurveGroup(port_pandl, instruments,
                                           capital=capital, 
                                           weighted_flag=True)

            return port_pandl

        port_pandl = self.parent.calc_or_cache(
            "portfolio", ALL_KEYNAME, _portfolio, self,  delayfill,
            roundpositions,
            flags="delayfill%sroundpositions%s" % (
             TorF(delayfill), TorF(roundpositions)))

        return port_pandl


if __name__ == '__main__':
    import doctest
    doctest.testmod()
