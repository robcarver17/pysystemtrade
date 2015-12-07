from systems.subsystem import SystemStage
from systems.defaults import system_defaults
from copy import copy

from syscore.objects import calc_or_cache, resolve_function
from syscore.pdutils import divide_df_single_column

class RawData(SystemStage):

    """
        A SystemStage that does some fairly common calculations before we do forecasting
            This is optional; forecasts can go straight to system.data
            The advantages of using RawData are: 
                   - preliminary calculations that are reused can be cached, to save time (eg volatility)
                   - preliminary calculations are available for inspection when diagnosing what is going on

    KEY INPUT: system.data.get_instrument_price(instrument_code)    
               found in self.get_instrument_price

    KEY OUTPUTS: system.rawdata.... several 

    Name: rawdata
    """    
    
    def __init__(self):
        """
        Create a new subsystem raw data object

        :returns: None
        """
        
        ## As with all subsystems any data that methods produce needs to be stored in a dict, indexed here
        delete_on_recalc=["_daily_returns_dict", "_daily_prices_dict", "_daily_vol_dict",  
                          "_norm_return_dict", "_price_dict", "_capped_norm_return_dict",
                           "_indexed_dict", "_daily_denominator_price_dict", "_daily_percentage_volatility"]

        ## Anything in this list wouldn't normally be deleted if we cleared a system of instrument data
        dont_delete=[]
        
        setattr(self, "_delete_on_recalc", delete_on_recalc)
        setattr(self, "_dont_recalc", dont_delete)

        setattr(self, "name", "rawdata")
    
    def get_instrument_price(self, instrument_code):
        """
        Gets the instrument price from the parent system.data object
                  
        KEY INPUT
                  
        :param instrument_code: Instrument to get prices for 
        :type trading_rules: str
        
        :returns: Tx1 pd.DataFrame

        >>> from systems.provided.example.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> system.rawdata.get_instrument_price("EDOLLAR").tail(2)
                      price
        2015-04-21  97.9050
        2015-04-22  97.8325
        """
        def _get_instrument_price(system, instrument_code):
            instrprice=system.data.get_instrument_price(instrument_code)
            return instrprice
    
        instrprice=calc_or_cache(self.parent, "_price_dict", instrument_code, _get_instrument_price)
        
        return instrprice
        
    
    def daily_prices(self, instrument_code):
        """
        Gets daily prices

        :param instrument_code: Instrument to get prices for 
        :type trading_rules: str
        
        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        >>> from systems.provided.example.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()

        >>> system=System([rawdata], data)
        >>> system.rawdata.daily_prices("EDOLLAR").tail(2)
                      price
        2015-04-21  97.9050
        2015-04-22  97.8325

        """
        def _daily_prices(system, instrument_code, this_subsystem):
            instrprice=this_subsystem.get_instrument_price(instrument_code)
            dailyprice=instrprice.resample("1B", how="last")
            return dailyprice
        
        dailyprice=calc_or_cache(self.parent, "_daily_prices_dict", instrument_code, _daily_prices, self)
        
        return dailyprice
    
    
    def daily_denominator_price(self, instrument_code):
        """
        Gets daily prices for use with % volatility
        This won't always be the same as the normal 'price' which is normally a cumulated total return series

        :param instrument_code: Instrument to get prices for 
        :type trading_rules: str
        
        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        >>> from systems.provided.example.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()

        >>> system=System([rawdata], data)
        >>> system.rawdata.daily_denominator_price("EDOLLAR").head(2)
                        price
        1983-09-26  71.416192
        1983-09-27  71.306192
        """
        def _daily_denominator_returns(system, instrument_code, this_subsystem):
            
            dem_returns=this_subsystem.daily_prices(instrument_code)
            return dem_returns
        
        dem_returns=calc_or_cache(self.parent, "_daily_denominator_price_dict", instrument_code, _daily_denominator_returns, self)
        
        return dem_returns
        
        
    
    
    def daily_returns(self, instrument_code):
        """
        Gets daily returns (not % returns)

        :param instrument_code: Instrument to get prices for 
        :type trading_rules: str
        
        :returns: Tx1 pd.DataFrame

        KEY OUTPUT

        >>> from systems.provided.example.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> system.rawdata.daily_returns("EDOLLAR").tail(2)
                     price
        2015-04-21 -0.0200
        2015-04-22 -0.0725
        """
        def _daily_returns(system, instrument_code, this_subsystem):
            instrdailyprice=this_subsystem.daily_prices(instrument_code)
            dailyreturn=instrdailyprice.diff()
            return dailyreturn
        
        dailyreturn=calc_or_cache(self.parent, "_daily_returns_dict", instrument_code, _daily_returns, self)
        
        return dailyreturn
    
    
        
    def daily_returns_volatility(self, instrument_code):
        """
        Gets volatility of daily returns (not % returns)
        
        This is done using a user defined function
        
        We can eithier inherit this from the config file, or pass eg: volconfig=dict(func="module.file.funcname, arg1=...)
        
        The dict must contain func key; anything else is optional

        KEY OUTPUT

        :param instrument_code: Instrument to get prices for 
        :type trading_rules: str
        
        :returns: Tx1 pd.DataFrame

        >>> from systems.provided.example.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> system.rawdata.daily_returns_volatility("EDOLLAR").tail(2)
                         vol
        2015-04-21  0.057053
        2015-04-22  0.058340
        >>>
        >>> from syscore.fileutils import get_pathname_for_package
        >>>
        >>> from sysdata.configdata import Config
        >>> config=Config(get_pathname_for_package("systems", ["provided","example", "exampleconfig.yaml"]))
        >>> system=System([rawdata], data, config)
        >>> system.rawdata.daily_returns_volatility("EDOLLAR").tail(2)
                         vol
        2015-04-21  0.057053
        2015-04-22  0.058340
        >>>
        >>> config=Config(dict(parameters=dict(volatility_calculation=dict(func="syscore.algos.robust_vol_calc", days=200))))
        >>> system=System([rawdata], data, config)
        >>> system.rawdata.daily_returns_volatility("EDOLLAR").tail(2)
                         vol
        2015-04-21  0.065903
        2015-04-22  0.066014
        
        """
        def _daily_returns_volatility(system, instrument_code,  this_subsystem):
            dailyreturns=this_subsystem.daily_returns(instrument_code)
            try:
                volconfig=copy(system.config.parameters['volatility_calculation'])
                identify_error="inherited from data object"
            except:
                volconfig=copy(system_defaults['volatility_calculation'])
                identify_error="found in system.defaults.py"

            if "func" not in volconfig:
                
                raise Exception("The volconfig dict (%s) needs to have a 'func' key" % identify_error)
            
            ## volconfig contains 'func' and some other arguments
            ## we turn func which could be a string into a function, and then call it with the other ags            
            volfunction=resolve_function(volconfig.pop('func'))
            vol=volfunction(dailyreturns, **volconfig)
            
            return vol
        
        vol=calc_or_cache(self.parent, "_daily_vol_dict", instrument_code, _daily_returns_volatility, self)
        
        return vol
            
        
    def get_daily_percentage_volatility(self, instrument_code):
        """
        Get percentage returns normalised by recent vol
        
        Useful statistic, also used for some trading rules
        
        This is an optional subsystem; forecasts can go straight to system.data
        :param instrument_code: Instrument to get prices for 
        :type trading_rules: str
        
        :returns: Tx1 pd.DataFrame
        
        >>> from systems.provided.example.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> system.rawdata.get_daily_percentage_volatility("EDOLLAR").tail(2)
                         vol
        2015-04-21  0.000583
        2015-04-22  0.000596        
        """
        def _get_daily_percentage_volatility(system, instrument_code, this_subsystem):
            denom_price=this_subsystem.daily_denominator_price(instrument_code)
            return_vol=this_subsystem.daily_returns_volatility(instrument_code)
            perc_vol=divide_df_single_column(return_vol, denom_price.shift(1))
            
            return perc_vol
        
        return calc_or_cache(self.parent, "_daily_percentage_volatility", instrument_code, _get_daily_percentage_volatility, self)



    def norm_returns(self, instrument_code):
        """
        Get returns normalised by recent vol
        
        Useful statistic, also used for some trading rules
        
        This is an optional subsystem; forecasts can go straight to system.data
        :param instrument_code: Instrument to get prices for 
        :type trading_rules: str
        
        :returns: Tx1 pd.DataFrame

        >>> from systems.provided.example.testdata import get_test_object
        >>> from systems.basesystem import System
        >>>
        >>> (rawdata, data, config)=get_test_object()
        >>> system=System([rawdata], data)
        >>> system.rawdata.norm_returns("EDOLLAR").tail(2)
                    norm_return
        2015-04-21    -0.342101
        2015-04-22    -1.270742
        """
        def _norm_returns(system, instrument_code, this_subsystem):
            returnvol=this_subsystem.daily_returns_volatility(instrument_code).shift(1)
            dailyreturns=this_subsystem.daily_returns(instrument_code)
            norm_return=divide_df_single_column(dailyreturns,returnvol)
            norm_return.columns=["norm_return"]
            return norm_return
        
        norm_returns=calc_or_cache(self.parent, "_norm_return_dict", instrument_code, _norm_returns, self)
        
        return norm_returns
    
        
if __name__ == '__main__':
    import doctest
    doctest.testmod()
