import pandas as pd
import numpy as np

from systems.subsystem import SubSystem
from syscore.objects import calc_or_cache
from syscore.pdutils import multiply_df, fix_weights_vs_pdm



class ForecastCombineFixed(SubSystem):
    """
    Subsystem for combining forecasts (already capped and scaled)
    
    KEY INPUT: system.forecastScaleCap.get_capped_forecast(instrument_code, rule_variation_name)

                found in self.get_capped_forecast(instrument_code, rule_variation_name)
                
    KEY OUTPUT: system.combForecast.get_combined_forecast(instrument_code)

    Name: combForecast
    """
    
    def __init__(self, forecast_weights=dict(), forecast_div_multiplier=dict()):
        """
        Create a SubSystem for combining forecasts
        
        If forecast_weights, and forecast_div_multiplier are not passed will get them from system.config
        
          
        :param forecast_weights: Dict or nested dict of weights 
        :type forecast_weights:    empty dict       (weights will be inherited from system.config)
                                dict (key names: rule variation names) of float 
                                nested dict (key names: instrument names; then rulevariation names) of float

        :param forecast_div_multiplier: float or dict of forecast multipliers
        :type forecast_div_multiplier: empty dict (f.d.m. will be inherited from system.config)
                                       float 
                                       dict of floats (key names: instrument names)
                
        """
        delete_on_recalc=['_combined_forecast']

        dont_delete=['_forecast_weights','_forecast_div_multiplier']
        
        setattr(self, "_delete_on_recalc", delete_on_recalc)
        setattr(self, "_dont_recalc", dont_delete)

        setattr(self, "name", "combForecast")

        setattr(self, "_passed_forecast_weights", forecast_weights)
        setattr(self, "_passed_forecast_div_multiplier", forecast_div_multiplier)
    
    def get_capped_forecast(self, instrument_code, rule_variation_name):
        """
        Get the capped forecast from the previous module
        
        KEY INPUT
        
        :param instrument_code: 
        :type str: 
        
        :param rule_variation_name:
        :type str: name of the trading rule variation
        
        :returns: dict of Tx1 pd.DataFrames; keynames rule_variation_name
        
        >>> from systems.provided.example.testdata import get_test_object_futures_with_rules_and_capping
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping()
        >>> system=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system.combForecast.get_capped_forecast("EDOLLAR","ewmac8").tail(2)
                      ewmac8
        2015-04-21  5.738741
        2015-04-22  5.061187
        """
        
        return self.parent.forecastScaleCap.get_capped_forecast(instrument_code, rule_variation_name)
        
        
    def get_forecast_weights(self, instrument_code):
        """
        Get the forecast weights for this instrument
        
        From: (a) passed into subsystem when created
              (b) ... if not found then: in system.config.instrument_weights
        
        :param instrument_code: 
        :type str: 

        :returns: TxK pd.DataFrame containing weights, columns are trading rule variation names, T covers all 

        >>> from systems.provided.example.testdata import get_test_object_futures_with_rules_and_capping
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping()
        >>> system=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> 
        >>> ## from config
        >>> system.combForecast.get_forecast_weights("EDOLLAR").tail(2)
                    ewmac16  ewmac8
        2015-04-21      0.5     0.5
        2015-04-22      0.5     0.5
        >>>
        >>> config.forecast_weights=dict(EDOLLAR=dict(ewmac8=0.9, ewmac16=0.1))
        >>> system2=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system2.combForecast.get_forecast_weights("EDOLLAR").tail(2)
                    ewmac16  ewmac8
        2015-04-21      0.1     0.9
        2015-04-22      0.1     0.9
        >>>
        >>> 
        >>> ## now with passed argumnents
        >>> system3=System([rawdata, rules, fcs, ForecastCombineFixed(forecast_weights=dict(ewmac8=0.6, ewmac16=0.4))], data, config)
        >>> system3.combForecast.get_forecast_weights("EDOLLAR").tail(2)
                    ewmac16  ewmac8
        2015-04-21      0.4     0.6
        2015-04-22      0.4     0.6
        >>>
        >>> system4=System([rawdata, rules, fcs, ForecastCombineFixed(forecast_weights=dict(EDOLLAR=dict(ewmac8=0.3, ewmac16=0.7)))], data, config)
        >>> system4.combForecast.get_forecast_weights("EDOLLAR").tail(2)
                    ewmac16  ewmac8
        2015-04-21      0.7     0.3
        2015-04-22      0.7     0.3
        """                    
        def _get_forecast_weight(system,  instrument_code,  this_subsystem ):

            
            if instrument_code in this_subsystem._passed_forecast_weights:
                fixed_weights=this_subsystem._passed_forecast_weights[instrument_code]
            elif len(this_subsystem._passed_forecast_weights)>0:
                ## must be a non nested dict
                fixed_weights=this_subsystem._passed_forecast_weights
            
            ## Okay we were passed a length zero dict; i.e. nothing
            ## Let's try the config
            elif "forecast_weights" in dir(system.config):
                
                if instrument_code in system.config.forecast_weights:
                    ## nested dict
                    fixed_weights=system.config.forecast_weights[instrument_code] 
                else:
                    ## assume it's a non nested dict
                    fixed_weights=system.config.forecast_weights
            else:
                raise Exception("Need to specify a dict of forecast_weights eithier in config.forecast_weights, or ForecastCombineFixed(forecast_weights=...)")
            
            ## Now we have a dict, fixed_weights.
            ## Need to turn into a timeseries covering the range of forecast dates
            rule_variation_list=list(fixed_weights.keys())
            rule_variation_list.sort()
            
            forecasts_ts=[
                            this_subsystem.get_capped_forecast(instrument_code, rule_variation_name).index 
                         for rule_variation_name in rule_variation_list]
            
            earliest_date=min([min(fts) for fts in forecasts_ts])
            latest_date=max([max(fts) for fts in forecasts_ts])

            ## this will be daily, but will be resampled later
            weight_ts=pd.date_range(start=earliest_date, end=latest_date)
            
            forecasts_weights=dict([
                            (rule_variation_name, pd.Series([fixed_weights[rule_variation_name]]*len(weight_ts), index=weight_ts)) 
                         for rule_variation_name in rule_variation_list])
            
            forecasts_weights=pd.concat(forecasts_weights, axis=1)
            forecasts_weights.columns=rule_variation_list

            return forecasts_weights
        
        forecast_weights=calc_or_cache(self.parent, "_forecast_weights", instrument_code,  _get_forecast_weight, self)
        return forecast_weights


    def get_forecast_diversification_multiplier(self, instrument_code):
        """
        
        Get the diversification multiplier for this instrument

        From: (a) passed into subsystem when created
              (b) ... if not found then: in system.config.instrument_weights
        
        :param instrument_code: instrument to get multiplier for
        :type instrument_code: str 

        :returns: Tx1 pd.DataFrame



        >>> from systems.provided.example.testdata import get_test_object_futures_with_rules_and_capping
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping()
        >>> system=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> 
        >>> ## from config
        >>> system.combForecast.get_forecast_diversification_multiplier("EDOLLAR").tail(2)
                    fdm
        2015-04-21  1.1
        2015-04-22  1.1
        >>>
        >>> config.forecast_div_multiplier=dict(EDOLLAR=2.0)
        >>> system2=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system2.combForecast.get_forecast_diversification_multiplier("EDOLLAR").tail(2)
                    fdm
        2015-04-21    2
        2015-04-22    2
        >>>
        >>> ## now with passed argumnents
        >>> system3=System([rawdata, rules, fcs, ForecastCombineFixed(forecast_div_multiplier=1.5)], data, config)
        >>> system3.combForecast.get_forecast_diversification_multiplier("EDOLLAR").tail(2)
                    fdm
        2015-04-21  1.5
        2015-04-22  1.5
        >>>
        >>> system4=System([rawdata, rules, fcs, ForecastCombineFixed(forecast_div_multiplier=2.5)], data, config)
        >>> system4.combForecast.get_forecast_diversification_multiplier("EDOLLAR").tail(2)
                    fdm
        2015-04-21  2.5
        2015-04-22  2.5

        """                    
        def _get_forecast_div_multiplier(system,  instrument_code,  this_subsystem ):
            
            if type(this_subsystem._passed_forecast_div_multiplier) is float:
                ## single value for all keys
                fixed_div_mult=this_subsystem._passed_forecast_div_multiplier
                
            elif instrument_code in this_subsystem._passed_forecast_div_multiplier.keys():
                ## Must be a dict
                fixed_div_mult=this_subsystem._passed_forecast_div_multiplier[instrument_code]
                
            ## Okay we were passed a length zero dict; i.e. nothing (or one missing the instrument at least)
            ## Let's try the config
            elif "forecast_div_multiplier" in dir(system.config):
                if type(system.config.forecast_div_multiplier) is float:
                    fixed_div_mult=system.config.forecast_div_multiplier
                    
                elif instrument_code in system.config.forecast_div_multiplier.keys():
                    ## dict
                    fixed_div_mult=system.config.forecast_div_multiplier[instrument_code] 
                else:
                    raise Exception("Missing key of %s in dict of forecast_div_multiplier in config" % instrument_code)
            else:
                raise Exception("Need to specify a dict of forecast_weights eithier in config.forecast_weights, or ForecastCombineFixed(forecast_weights=...)")
            
            ## Now we have a dict, fixed_weights.
            ## Need to turn into a timeseries covering the range of forecast dates
            ## get forecast weights first
            forecast_weights=this_subsystem.get_forecast_weights(instrument_code)
            weight_ts=forecast_weights.index
            
            ts_fdm=pd.Series([fixed_div_mult]*len(weight_ts), index=weight_ts)
            ts_fdm=ts_fdm.to_frame("fdm")
            
            return ts_fdm
        
        forecast_div_multiplier=calc_or_cache(self.parent, '_forecast_div_multiplier', instrument_code,  _get_forecast_div_multiplier, self)
        return forecast_div_multiplier
    
        
    def get_combined_forecast(self, instrument_code):
        """
        Get a combined forecast, linear combination of individual forecasts with FDM applied
        
        We forward fill all forecasts. We then adjust forecast weights so that they are 1.0 in every
          period; after setting to zero when no forecast is available. Finally we multiply up, and
          apply the FDM.

        :param instrument_code: 
        :type str: 
        
        :returns: Tx1 pd.DataFrame
        
        KEY OUTPUT


        >>> from systems.provided.example.testdata import get_test_object_futures_with_rules_and_capping
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping()
        >>> system=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> 
        >>> system.combForecast.get_combined_forecast("EDOLLAR").tail(2)
                    comb_forecast
        2015-04-21       7.622781
        2015-04-22       6.722785
        """                    
        def _get_combined_forecast(system,  instrument_code,  this_subsystem ):
            
            forecast_weights=this_subsystem.get_forecast_weights(instrument_code)
            rule_variation_list=list(forecast_weights.columns)
            forecasts=[this_subsystem.get_capped_forecast(instrument_code, rule_variation_name) for rule_variation_name in rule_variation_list]
            forecast_div_multiplier=this_subsystem.get_forecast_diversification_multiplier(instrument_code)

            forecasts=pd.concat(forecasts, axis=1)
                
            ## adjust weights for missing data
            forecast_weights=fix_weights_vs_pdm(forecast_weights, forecasts)

            ## multiply weights by forecasts

            combined_forecast=multiply_df(forecast_weights, forecasts)
            
            ## sum
            combined_forecast=combined_forecast.sum(axis=1).to_frame("comb_forecast") 
            
            ## apply fdm
            ## (note in this simple version we aren't adjusting FDM if forecast_weights change)
            forecast_div_multiplier=forecast_div_multiplier.reindex(forecasts.index, method="ffill")
            combined_forecast=multiply_df(combined_forecast,forecast_div_multiplier)
            
            return combined_forecast
        
        combined_forecast=calc_or_cache(self.parent, '_combined_forecast', instrument_code,  _get_combined_forecast, self)
        return combined_forecast



if __name__ == '__main__':
    import doctest
    doctest.testmod()
