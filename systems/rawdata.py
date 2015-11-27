from systems.subsystem import SubSystem
from systems.defaults import system_defaults
from copy import copy

from syscore.objects import calc_or_cache, resolve_function


class subSystemRawData(SubSystem):
    
    def __init__(self):
        """
        A SubSystem that does some fairly common calculations before we do forecasting
            This is optional; forecasts can go straight to system.data
        """
        delete_on_recalc=["_daily_returns_dict", "_daily_prices_dict", "_daily_vol_dict",  
                          "_norm_return_dict", "_price_dict", "_capped_norm_return_dict",
                           "_indexed_dict"]

        dont_delete=[]
        
        setattr(self, "_delete_on_recalc", delete_on_recalc)
        setattr(self, "_dont_recalc", dont_delete)

        setattr(self, "name", "rawdata")
    
    def get_instrument_price(self, instrument_code):
            """
            Gets the instrument price
            """
            def _get_instrument_price(system, instrument_code):
                instrprice=system.data.get_instrument_price(instrument_code)
                return instrprice
        
            return calc_or_cache(self.parent, "_price_dict", instrument_code, _get_instrument_price)
        
    
    def daily_prices(self, instrument_code):
        """
        Gets daily prices
        """
        def _daily_prices(system, instrument_code):
            instrprice=system.rawdata.get_instrument_price(instrument_code)
            dailyprice=instrprice.resample("1B", how="last")
            return dailyprice
        
        return calc_or_cache(self.parent, "_daily_prices_dict", instrument_code, _daily_prices)
    
    def daily_returns(self, instrument_code):
        """
        Gets daily returns (not % returns)
        """
        def _daily_returns(system, instrument_code):
            instrdailyprice=system.rawdata.daily_prices(instrument_code)
            dailyreturn=instrdailyprice.diff()
            return dailyreturn
        
        return calc_or_cache(self.parent, "_daily_returns_dict", instrument_code, _daily_returns)
        
    def daily_returns_volatility(self, instrument_code, volconfig=None):
        """
        Gets volatility of daily returns (not % returns)
        
        This is done using a user defined function
        
        We can eithier inherit this from the config file, or pass eg: volconfig=dict(func="module.file.funcname, arg1=...)
        
        The dict must contain func key; anything else is optional
        """
        def _daily_returns_volatility(system, instrument_code, volconfig):
            dailyreturns=system.rawdata.daily_returns(instrument_code)
            if volconfig is None:
                try:
                    volconfig=copy(system.config.parameters['volatility_calculation'])
                    identify_error="inherited from data object"
                except:
                    volconfig=system_defaults['volatility_calculation']
                    identify_error="found in system.defaults.py"

            else:
                identify_error="passed directly into method call"

            if "func" not in volconfig:
                
                raise Exception("The volconfig dict (%s) needs to have a 'func' key" % identify_error)
            
            ## volconfig contains 'func' and some other arguments
            ## we turn func which could be a string into a function, and then call it with the other ags            
            volfunction=resolve_function(volconfig.pop('func'))
            vol=volfunction(dailyreturns, **volconfig)
            
            return vol
        
        return calc_or_cache(self.parent, "_daily_vol_dict", instrument_code, _daily_returns_volatility, volconfig)
            
        
        

    def norm_returns(self, instrument_code):
        """
        Get returns normalised by recent vol
        
        Useful statistic, also used for some trading rules
        
        This is an optional subsystem; forecasts can go straight to system.data
    
        """
        def _norm_returns(system, instrument_code):
            returnvol=system.rawdata.daily_returns_volatility(instrument_code).shift(1)
            dailyreturns=system.rawdata.daily_returns(instrument_code)
            norm_return=dailyreturns.iloc[:,0]/returnvol.iloc[:,0]
            return norm_return.to_frame()
        
        return calc_or_cache(self.parent, "_norm_return_dict", instrument_code, _norm_returns)
        
