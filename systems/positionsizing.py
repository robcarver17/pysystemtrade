
from systems.stage import SystemStage
from systems.defaults import system_defaults
from syscore.objects import calc_or_cache, ALL_KEYNAME
from syscore.pdutils import multiply_df_single_column, divide_df_single_column
from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.algos import robust_vol_calc

class PositionSizing(SystemStage):
    """
    Stage for position sizing (take combined forecast; turn into subsystem positions)
    
    KEY INPUTS: a) system.combForecast.get_combined_forecast(instrument_code)
                 found in self.get_combined_forecast
                
                b) system.rawdata.get_daily_percentage_volatility(instrument_code)
                 found in self.get_price_volatility(instrument_code)
                 
                 If not found, uses system.data.get_instrument_price to calculate
                   
                c) system.rawdata.daily_denominator_price((instrument_code)
                 found in self.get_instrument_sizing_data(instrument_code)

                If not found, uses system.data.get_instrument_price 

                d)  system.data.get_value_of_block_price_move(instrument_code)
                 found in self.get_instrument_sizing_data(instrument_code)
                   
                e)  system.data.get_fx_for_instrument(instrument_code, base_currency)
                   found in self.get_fx_rate(instrument_code)
                
                
    KEY OUTPUT: system.positionSize.get_subsystem_position(instrument_code)

    Name: positionSize
    """
    
    def __init__(self):
        """
        Create a SystemStage for combining forecasts
        
                
        """
        delete_on_recalc=['_block_value', '_instrument_currency_vol','_instrument_value_vol',
                          '_vol_scalar','_subsystem_position', '_fx_rate']

        dont_delete=['_vol_target']
        
        setattr(self, "_delete_on_recalc", delete_on_recalc)
        setattr(self, "_dont_recalc", dont_delete)

        setattr(self, "name", "positionSize")
        
    def get_combined_forecast(self, instrument_code):
        """
        Get the combined forecast from previous module
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 
        
        KEY INPUT
        
        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> system.positionSize.get_combined_forecast("EDOLLAR").tail(2)
                    comb_forecast
        2015-04-21       7.622781
        2015-04-22       6.722785

        """

        return self.parent.combForecast.get_combined_forecast(instrument_code)
    
    def get_price_volatility(self, instrument_code):
        """
        Get the daily % volatility 
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 
        
        KEY INPUT

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> system.positionSize.get_price_volatility("EDOLLAR").tail(2)
                         vol
        2015-04-21  0.058307
        2015-04-22  0.059634
        >>>
        >>> system2=System([ rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> system2.positionSize.get_price_volatility("EDOLLAR").tail(2)
                         vol
        2015-04-21  0.058274
        2015-04-22  0.059632
        """
        if hasattr(self.parent, "rawdata"):
            daily_perc_vol=self.parent.rawdata.get_daily_percentage_volatility(instrument_code)
        else:
            price=self.parent.data.get_instrument_price(instrument_code)
            price=price.resample("1B", how="last")
            return_vol=robust_vol_calc(price.diff())
            daily_perc_vol=100.0*divide_df_single_column(return_vol,price)
            
        return daily_perc_vol




    def get_instrument_sizing_data(self, instrument_code):
        """
        Get various things from data and rawdata to calculate position sizes
        
        KEY INPUT
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: tuple (Tx1 pd.DataFrame: underlying price [as used to work out % volatility], 
                              float: value of price block move) 

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> ans=system.positionSize.get_instrument_sizing_data("EDOLLAR")
        >>> ans[0].tail(2)
                    price
        2015-04-21  97.83
        2015-04-22    NaN
        >>>
        >>> ans[1]
        2500
        >>>
        >>> system=System([rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> ans=system.positionSize.get_instrument_sizing_data("EDOLLAR")
        >>> ans[0].tail(2)
                      price
        2015-04-21  97.9050
        2015-04-22  97.8325        
        >>>
        >>> ans[1]
        2500


        """

        if hasattr(self.parent, "rawdata"):
            underlying_price=self.parent.rawdata.daily_denominator_price(instrument_code)

        else:
            underlying_price=self.parent.data.get_instrument_price(instrument_code)
            underlying_price=underlying_price.resample("1B", how="last")
        
        value_of_price_move=self.parent.data.get_value_of_block_price_move(instrument_code)
    
        return (underlying_price, value_of_price_move)



    def get_daily_cash_vol_target(self):
        """
        Get the daily cash vol target
       
        Requires: percentage_vol_target, notional_trading_capital, base_currency
        
        To find these, look in (a) arguments passed when subsystem created
                (b).... if not found, in system.config.parameters...
                (c).... if not found, in systems.get_defaults.py

        
        :Returns: tuple (str, float): str is base_currency, float is value 

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>>
        >>> ## from config 
        >>> system.positionSize.get_daily_cash_vol_target()['base_currency']
        'GBP'
        >>>
        >>> ## from defaults
        >>> del(config.base_currency)
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> system.positionSize.get_daily_cash_vol_target()['base_currency']
        'USD'
        >>>
        
        """

        def _get_vol_target(system,  an_ignored_variable,  this_stage ):

            try:
                percentage_vol_target=system.config.percentage_vol_target
            except:
                percentage_vol_target=system_defaults['percentage_vol_target']
                    
            try:
                notional_trading_capital=system.config.notional_trading_capital
            except:
                notional_trading_capital=system_defaults['notional_trading_capital']
                    
            try:
                base_currency=system.config.base_currency
            except:
                base_currency=system_defaults['base_currency']

            annual_cash_vol_target=notional_trading_capital*percentage_vol_target/100.0
            daily_cash_vol_target=annual_cash_vol_target/ROOT_BDAYS_INYEAR
            
            vol_target_dict=dict(base_currency=base_currency, percentage_vol_target=percentage_vol_target, 
                                 notional_trading_capital=notional_trading_capital, annual_cash_vol_target=annual_cash_vol_target, 
                                 daily_cash_vol_target=daily_cash_vol_target)
            
            return vol_target_dict
        
        vol_target_dict=calc_or_cache(self.parent, '_vol_target', ALL_KEYNAME,  _get_vol_target, self)
        return vol_target_dict
    

    def get_fx_rate(self, instrument_code):
        """
        Get FX rate to translate instrument volatility into same currency as account value.
        
        KEY INPUT
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame: fx rate

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> system.positionSize.get_fx_rate("EDOLLAR").tail(2)
                          fx
        2015-10-30  0.654270
        2015-11-02  0.650542
        """

        def _get_fx_rate(system,  instrument_code,  this_stage ):
            base_currency=this_stage.get_daily_cash_vol_target()['base_currency']
            fx_rate=system.data.get_fx_for_instrument(instrument_code, base_currency)
    
            return fx_rate
            
        fx_rate=calc_or_cache(self.parent, '_fx_rate', instrument_code,  _get_fx_rate, self)
        
        return fx_rate
        
    
    def get_block_value(self, instrument_code):
        """
        Calculate block value for instrument_code

        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> system.positionSize.get_block_value("EDOLLAR").tail(2)
                      price
        2015-04-21  2445.75
        2015-04-22      NaN
        >>>
        >>> system=System([rules, fcs, comb, PositionSizing()], data, config)
        >>> system.positionSize.get_block_value("EDOLLAR").tail(2)
                        price
        2015-04-21  2447.6250
        2015-04-22  2445.8125

        """                    
        def _get_block_value(system,  instrument_code,  this_stage ):
            
            (underlying_price, value_of_price_move)=this_stage.get_instrument_sizing_data(instrument_code)
            block_value=0.01*underlying_price*value_of_price_move
            
            return block_value
        
        block_value=calc_or_cache(self.parent, '_block_value', instrument_code,  _get_block_value, self)
        return block_value


    def get_instrument_currency_vol(self, instrument_code):
        """
        Get value of volatility of instrument in instrument's own currency 
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> system.positionSize.get_instrument_currency_vol("EDOLLAR").tail(2)
                           icv
        2015-04-21  142.603997
        2015-04-22  145.849773
        >>>
        >>> system2=System([ rules, fcs, comb, PositionSizing()], data, config)
        >>> system2.positionSize.get_instrument_currency_vol("EDOLLAR").tail(2)
                           icv
        2015-04-21  142.633151
        2015-04-22  145.849773
        
        """
        def _get_instrument_currency_vol(system,  instrument_code,  this_stage ):
            
            block_value=this_stage.get_block_value(instrument_code)
            daily_perc_vol=this_stage.get_price_volatility(instrument_code)
            
            instr_ccy_vol=multiply_df_single_column(block_value, daily_perc_vol, ffill=(True, False))
            instr_ccy_vol.columns=['icv']
            
            return instr_ccy_vol

        
        instr_ccy_vol=calc_or_cache(self.parent, '_instrument_currency_vol', instrument_code,  _get_instrument_currency_vol, self)
        return instr_ccy_vol

    def get_instrument_value_vol(self, instrument_code):
        """
        Get value of volatility of instrument in base currency (used for account value) 
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> system.positionSize.get_instrument_value_vol("EDOLLAR").tail(2)
                          ivv
        2015-04-21  95.408349
        2015-04-22  97.782721
        >>> 
        >>> system2=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> system2.positionSize.get_instrument_value_vol("EDOLLAR").tail(2)
                          ivv
        2015-04-21  95.408349
        2015-04-22  97.782721
        
        """
        def _get_instrument_value_vol(system,  instrument_code,  this_stage ):
            
            instr_ccy_vol=this_stage.get_instrument_currency_vol(instrument_code)
            fx_rate=this_stage.get_fx_rate(instrument_code)            

            instr_value_vol=multiply_df_single_column(instr_ccy_vol, fx_rate, ffill=(False, True))
            instr_value_vol.columns=['ivv']
            
            return instr_value_vol

        
        instr_value_vol=calc_or_cache(self.parent, '_instrument_value_vol', instrument_code,  _get_instrument_value_vol, self)
        return instr_value_vol
    

    
    def get_volatility_scalar(self, instrument_code):
        """
        Get ratio of required volatility vs volatility of instrument in instrument's own currency 
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> system.positionSize.get_volatility_scalar("EDOLLAR").tail(2)
                      vol_scalar
        2015-04-21     10.481263
        2015-04-22     10.226755
        >>> 
        >>> system2=System([ rules, fcs, comb, PositionSizing()], data, config)
        >>> system2.positionSize.get_volatility_scalar("EDOLLAR").tail(2)
                      vol_scalar
        2015-04-21    10.479121
        2015-04-22    10.226756

        """
        def _get_volatility_scalar(system,  instrument_code,  this_stage ):
            
            instr_value_vol=this_stage.get_instrument_value_vol(instrument_code)
            cash_vol_target=this_stage.get_daily_cash_vol_target()['daily_cash_vol_target']
            
            vol_scalar=cash_vol_target/ instr_value_vol
            vol_scalar.columns=['vol_scalar']
                        
            return vol_scalar

        vol_scalar=calc_or_cache(self.parent, '_vol_scalar', instrument_code,  _get_volatility_scalar, self)
        return vol_scalar

    
    def get_subsystem_position(self, instrument_code):
        """
        Get scaled position (assuming for now we trade our entire capital for one instrument) 

        KEY OUTPUT 
        
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        
        :returns: Tx1 pd.DataFrame 

        >>> from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
        >>> from systems.basesystem import System
        >>> (comb, fcs, rules, rawdata, data, config)=get_test_object_futures_with_comb_forecasts()
        >>> system=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> 
        >>> system.positionSize.get_subsystem_position("EDOLLAR").tail(2)
                    ss_position
        2015-04-21     7.989637
        2015-04-22     6.875228
        >>> 
        >>> system2=System([rawdata, rules, fcs, comb, PositionSizing()], data, config)
        >>> system2.positionSize.get_subsystem_position("EDOLLAR").tail(2)
                    ss_position
        2015-04-21     7.989637
        2015-04-22     6.875228

        """
        def _get_subsystem_position(system,  instrument_code,  this_stage ):
            
            avg_abs_forecast=system_defaults['average_absolute_forecast']
            
            vol_scalar=this_stage.get_volatility_scalar(instrument_code)
            forecast=this_stage.get_combined_forecast(instrument_code)
            
            subsystem_position=multiply_df_single_column(vol_scalar, forecast, ffill=(True, False))/avg_abs_forecast
            subsystem_position.columns=['ss_position'] 
                                   
            return subsystem_position

        
        subsystem_position=calc_or_cache(self.parent, '_subsystem_position', instrument_code,  _get_subsystem_position, self)
        return subsystem_position

if __name__ == '__main__':
    import doctest
    doctest.testmod()
