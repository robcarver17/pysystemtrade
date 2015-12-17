import pandas as pd

from syscore.accounting import  pandl
from systems.stage import SystemStage
from systems.basesystem import ALL_KEYNAME
from syscore.pdutils import multiply_df_single_column,  fix_weights_vs_pdm
from examples.introduction.asimpletradingrule import instrument_code

class Account(SystemStage):
    """
    SystemStage for accounting
    
    KEY INPUT: 
                found in self.get_forecast(instrument_code, rule_variation)

                found in self.get_forecast_weights_and_fdm(instrument_code)

                system.positionSize.get_subsystem_position(instrument_code)
                found in self.get_subsystem_position(instrument_code)
                
                found in self.get_portfolio_position()
                
                found in self.get_instrument_weights_and_idm(instrument_code)

                found in self.get_capital()

                
    KEY OUTPUT: self.forecasts()
                (will be used to optimise forecast weights in future version)
                
                self.instruments()
                (will be used to optimise instrument weights in future version)
                

    Name: accounts
    """
    
    def __init__(self):
        """
        Create a SystemStage for accounting
        
        
                
        """

        protected=[]        
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
        
        :returns: dict of Tx1 pd.DataFrames
        
        """
        return self.parent.forecastScaleCap.get_capped_forecast(instrument_code, rule_variation_name)

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
        
    def get_instrument_div_multiplier(self):
        """
        Get instrument div mult 
        
        :returns: Tx1 pd.DataFrame 
        
        KEY INPUT
        

        """

        return self.parent.portfolio.get_instrument_diversification_multiplier()
    
    def get_forecast_div_multiplier(self, instrument_code):
        """
        Get the f.d.m from the previous module
        
        KEY INPUT
        
        :param instrument_code: 
        :type str: 
        
        :returns: dict of Tx1 pd.DataFrames
        
        """
        return self.parent.combForecast.get_forecast_diversification_multiplier(instrument_code)
    
    def get_instrument_weights(self):
        """
        Get instrument weights
        
        
        :returns: Tx1 pd.DataFrame 
        
        KEY INPUT
        

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
        
        KEY INPUT
        
        """
        return list(self.parent.rules.trading_rules().keys())
        
    def get_instrument_list(self):
        """
        Get the trading rules for this instrument, from a previous module
        
        :returns: list of str 
        
        KEY INPUT
        
        """
        return self.parent.portfolio.get_instrument_list()

    def get_rule_groups(self):
        """
        Get the rule groups from the config
        
        :returns: nested dict
        """
        return getattr(self.parent.config, "rule_groups", dict())

    def get_style_groups(self):
        """
        Get the style groups from the config
        
        :returns: nested dict
        
        
        """
        return getattr(self.parent.config, "style_groups", dict())

    def get_notional_capital(self):
        """
        
        dict(base_currency=base_currency,notional_trading_capital=notional_trading_capital,...)
        """
        return self.parent.positionSize.get_daily_cash_vol_target()

    def get_fx_rate(self, instrument_code):
        return self.parent.positionSize.get_fx_rate(instrument_code)

    def get_notional_position(self):
        """
        Get all the notional position from a previous module
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 
        
        KEY INPUT
        
        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.get_notional_positions()
        
        """
        return self.parent.portfolio.get_notional_position(instrument_code)

    def get_instrument_price(self, instrument_code):
        ## cache as get from data
        return self.parent.data.get_instrument_price(instrument_code)

    def get_value_of_price_move(self, instrument_code):
        
        (not_used, value_of_price_move)=self.parent.positionSize.get_instrument_sizing_data(instrument_code)
        
        return value_of_price_move

    def get_daily_returns_volatility(self, instrument_code):
        if hasattr(self.parent, "rawdata"):
            return_vol=self.parent.rawdata.daily_returns_volatility(instrument_code)
        else:
            price=self.parent.data.get_instrument_price(instrument_code)
            price=price.resample("1B", how="last")
            return_vol=robust_vol_calc(price.diff())

        return return_vol
    
    def pandl_for_instrument(self, instrument_code, percentage=True, delayfill=True, roundpositions=False):
        """
        """
        price=self.get_instrument_price(instrument_code)
        positions=self.get_notional_position(instrument_code)
        fx=self.get_fx_rate(instrument_code)
        value_of_price_point=self.get_value_of_price_move(instrument_code)
        pandl(price=price,  positions=positions, delayfill=delayfill, roundpositions=roundpositions, 
                        fx=fx, value_of_price_point=value_of_price_point )

    def pandl_for_instrument_forecast(self, instrument_code, rule_variation_name, delayfill=True):
        price=self.get_instrument_price(instrument_code)
        forecast=self.get_capped_forecast(instrument_code, rule_variation_name)
        price_change_volatility=self.get_price_change_volatility(instrument_code)
        pandl(price=price,   delayfill=delayfill,  price_change_volatility=price_change_volatility, forecast=forecast)
        
    def portfolio(self):
        pass

    """    
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
