import pandas as pd

from systems.stage import SystemStage
from syscore.pdutils import multiply_df, fix_weights_vs_pdm
from systems.defaults import system_defaults


class ForecastCombineFixed(SystemStage):
    """
    Stage for combining forecasts (already capped and scaled)
    
    KEY INPUT: system.forecastScaleCap.get_capped_forecast(instrument_code, rule_variation_name)

                found in self.get_capped_forecast(instrument_code, rule_variation_name)
                
    KEY OUTPUT: system.combForecast.get_combined_forecast(instrument_code)

    Name: combForecast
    """
    
    def __init__(self):
        """
        Create a SystemStage for combining forecasts
        
                
        """

        protected=['get_forecast_weights','get_forecast_diversification_multiplier']
        setattr(self, "_protected", protected)

        setattr(self, "name", "combForecast")
    
    def get_capped_forecast(self, instrument_code, rule_variation_name):
        """
        Get the capped forecast from the previous module
        
        KEY INPUT
        
        :param instrument_code: 
        :type str: 
        
        :param rule_variation_name:
        :type str: name of the trading rule variation
        
        :returns: dict of Tx1 pd.DataFrames; keynames rule_variation_name
        
        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping
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

        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping
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
        >>> del(config.forecast_weights)
        >>> system3=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system3.combForecast.get_forecast_weights("EDOLLAR").tail(2)
        WARNING: No forecast weights  - using equal weights of 0.5000 over all 2 trading rules in system
                    ewmac16  ewmac8
        2015-04-21      0.5     0.5
        2015-04-22      0.5     0.5
        """                    
        def _get_forecast_weights(system,  instrument_code,  this_stage ):

            ## Let's try the config
            if "forecast_weights" in dir(system.config):
                
                if instrument_code in system.config.forecast_weights:
                    ## nested dict
                    fixed_weights=system.config.forecast_weights[instrument_code] 
                else:
                    ## assume it's a non nested dict
                    fixed_weights=system.config.forecast_weights
            else:
                rules=list(self.parent.rules.trading_rules().keys())
                weight=1.0/len(rules)

                print("WARNING: No forecast weights  - using equal weights of %.4f over all %d trading rules in system" % (weight, len(rules)))
                fixed_weights=dict([(rule_name, weight) for rule_name in rules])
                
            
            ## Now we have a dict, fixed_weights.
            ## Need to turn into a timeseries covering the range of forecast dates
            rule_variation_list=list(fixed_weights.keys())
            rule_variation_list.sort()
            
            forecasts_ts=[
                            this_stage.get_capped_forecast(instrument_code, rule_variation_name).index 
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
        
        forecast_weights=self.parent.calc_or_cache( "get_forecast_weights", instrument_code,  _get_forecast_weights, self)
        return forecast_weights


    def get_forecast_diversification_multiplier(self, instrument_code):
        """
        
        Get the diversification multiplier for this instrument

        From: system.config.instrument_weights
        
        :param instrument_code: instrument to get multiplier for
        :type instrument_code: str 

        :returns: Tx1 pd.DataFrame



        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping
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
        >>> ## defaults
        >>> del(config.forecast_div_multiplier)
        >>> system3=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system3.combForecast.get_forecast_diversification_multiplier("EDOLLAR").tail(2)
                    fdm
        2015-04-21    1
        2015-04-22    1
        """                    
        def _get_forecast_div_multiplier(system,  instrument_code,  this_stage ):
            
            ## Let's try the config
            if hasattr(system.config, "forecast_div_multiplier"):
                if type(system.config.forecast_div_multiplier) is float:
                    fixed_div_mult=system.config.forecast_div_multiplier
                    
                elif instrument_code in system.config.forecast_div_multiplier.keys():
                    ## dict
                    fixed_div_mult=system.config.forecast_div_multiplier[instrument_code] 
                else:
                    raise Exception("FDM in config needs to be eithier float, or dict with instrument_code keys")

            elif "forecast_div_multiplier" in system_defaults:
                ## try defaults
                fixed_div_mult=system_defaults['forecast_div_multiplier']
            else:
                raise Exception("Need to specify FDM in config or system_defaults")
            
            ## Now we have a dict, fixed_weights.
            ## Need to turn into a timeseries covering the range of forecast dates
            ## get forecast weights first
            forecast_weights=this_stage.get_forecast_weights(instrument_code)
            weight_ts=forecast_weights.index
            
            ts_fdm=pd.Series([fixed_div_mult]*len(weight_ts), index=weight_ts)
            ts_fdm=ts_fdm.to_frame("fdm")
            
            return ts_fdm
        
        forecast_div_multiplier=self.parent.calc_or_cache( 'get_forecast_diversification_multiplier', instrument_code,  _get_forecast_div_multiplier, self)
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


        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping()
        >>> system=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> 
        >>> system.combForecast.get_combined_forecast("EDOLLAR").tail(2)
                    comb_forecast
        2015-04-21       7.622781
        2015-04-22       6.722785
        """                    
        def _get_combined_forecast(system,  instrument_code,  this_stage ):
            
            forecast_weights=this_stage.get_forecast_weights(instrument_code)
            rule_variation_list=list(forecast_weights.columns)
            forecasts=[this_stage.get_capped_forecast(instrument_code, rule_variation_name) for rule_variation_name in rule_variation_list]
            forecast_div_multiplier=this_stage.get_forecast_diversification_multiplier(instrument_code)

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
        
        combined_forecast=self.parent.calc_or_cache( 'get_combined_forecast', instrument_code,  _get_combined_forecast, self)
        return combined_forecast



if __name__ == '__main__':
    import doctest
    doctest.testmod()
