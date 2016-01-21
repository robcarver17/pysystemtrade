import pandas as pd
from copy import copy


from syscore.genutils import str2Bool
from syscore.pdutils import multiply_df, fix_weights_vs_pdm, apply_cap
from syscore.objects import resolve_function

from systems.defaults import system_defaults
from systems.stage import SystemStage
from systems.basesystem import ALL_KEYNAME

class ForecastCombineFixed(SystemStage):
    """
    Stage for combining forecasts (already capped and scaled)

    KEY INPUT: system.forecastScaleCap.get_capped_forecast(instrument_code, rule_variation_name)
                found in self.get_capped_forecast(instrument_code, rule_variation_name)

                system.forecastScaleCap.get_forecast_cap()
                found in self.get_forecast_cap()
                
                system.rules.trading_rules()
                found in self.get_trading_rule_list(instrument_code)

    KEY OUTPUT: system.combForecast.get_combined_forecast(instrument_code)

    Name: combForecast
    """

    def __init__(self):
        """
        Create a SystemStage for combining forecasts


        """

        protected = ['get_forecast_weights',
                     'get_forecast_diversification_multiplier']
        setattr(self, "_protected", protected)

        setattr(self, "name", "combForecast")

    def get_forecast_cap(self):
        """
        Get the forecast cap from the previous module

        :returns: float

        KEY INPUT
        """

        return self.parent.forecastScaleCap.get_forecast_cap()

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
        2015-12-10 -0.190583
        2015-12-11  0.871231
        """

        return self.parent.forecastScaleCap.get_capped_forecast(
            instrument_code, rule_variation_name)

    def get_trading_rule_list(self, instrument_code):
        """
        Get list of all trading rule names

        If we have fixed weights use those; otherwise get from trading rules

        KEY INPUT

        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping()
        >>> system=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>>
        >>> system.combForecast.get_trading_rule_list("EDOLLAR")
        ['ewmac16', 'ewmac8']
        """
        # Let's try the config
        system=self.parent
        if hasattr(system.config, "forecast_weights"):
            ## a dict of weights, nested or un nested
            if instrument_code in system.config.forecast_weights:
                # nested dict
                rules = system.config.forecast_weights[
                    instrument_code].keys()
            else:
                # assume it's a non nested dict
                rules = system.config.forecast_weights.keys()
        else:
            ## not supplied in config
            rules = self.parent.rules.trading_rules().keys()
            
        rules = list(rules)
        rules.sort()

        return rules

    def get_all_forecasts(self, instrument_code, rule_variation_list=None):
        """
        Returns a time series of forecasts for a particular instrument

        KEY INPUT

        :param instrument_code:
        :type str:

        :param rule_variation_list:
        :type list: list of str to get forecasts for, if None uses get_trading_rule_list

        :returns: TxN pd.DataFrames; columns rule_variation_name

        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping()
        >>> system1=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system1.combForecast.get_all_forecasts("EDOLLAR",["ewmac8"]).tail(2)
                      ewmac8
        2015-12-10 -0.190583
        2015-12-11  0.871231
        >>>
        >>> system2=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system2.combForecast.get_all_forecasts("EDOLLAR").tail(2)
                     ewmac16    ewmac8
        2015-12-10  3.134462 -0.190583
        2015-12-11  3.606243  0.871231
        """
        def _get_all_forecasts(system, instrument_code, this_stage, rule_variation_list):

            if rule_variation_list is None:
                rule_variation_list=this_stage.get_trading_rule_list(instrument_code)
    
            forecasts = [
                this_stage.get_capped_forecast(
                    instrument_code,
                    rule_variation_name) for rule_variation_name in rule_variation_list]
    
            forecasts = pd.concat(forecasts, axis=1)
            
            forecasts.columns = rule_variation_list
            
            forecasts = forecasts.ffill()
            
            return forecasts

        forecasts = self.parent.calc_or_cache(
            "get_all_forecasts", instrument_code, _get_all_forecasts, self, rule_variation_list)
        
        return forecasts

    def get_raw_forecast_weights(self, instrument_code):
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
        >>> system.combForecast.get_raw_forecast_weights("EDOLLAR").tail(2)
                    ewmac16  ewmac8
        2015-12-10      0.5     0.5
        2015-12-11      0.5     0.5
        >>>
        >>> config.forecast_weights=dict(EDOLLAR=dict(ewmac8=0.9, ewmac16=0.1))
        >>> system2=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system2.combForecast.get_raw_forecast_weights("EDOLLAR").tail(2)
                    ewmac16  ewmac8
        2015-12-10      0.1     0.9
        2015-12-11      0.1     0.9
        >>>
        >>> del(config.forecast_weights)
        >>> system3=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system3.combForecast.get_raw_forecast_weights("EDOLLAR").tail(2)
        WARNING: No forecast weights  - using equal weights of 0.5000 over all 2 trading rules in system
                    ewmac16  ewmac8
        2015-12-10      0.5     0.5
        2015-12-11      0.5     0.5
        """
        def _get_raw_forecast_weights(system, instrument_code, this_stage):

            # Let's try the config
            if "forecast_weights" in dir(system.config):

                if instrument_code in system.config.forecast_weights:
                    # nested dict
                    fixed_weights = system.config.forecast_weights[
                        instrument_code]
                else:
                    # assume it's a non nested dict
                    fixed_weights = system.config.forecast_weights
            else:
                rules = this_stage.get_trading_rule_list(instrument_code)
                weight = 1.0 / len(rules)

                print(
                    "WARNING: No forecast weights  - using equal weights of %.4f over all %d trading rules in system" %
                    (weight, len(rules)))
                fixed_weights = dict([(rule_name, weight)
                                      for rule_name in rules])

            # Now we have a dict, fixed_weights.
            # Need to turn into a timeseries covering the range of forecast
            # dates
            rule_variation_list = sorted(fixed_weights.keys())

            forecasts_ts = this_stage.get_all_forecasts(instrument_code, rule_variation_list)

            earliest_date = forecasts_ts.index[0]
            latest_date = forecasts_ts.index[-1]

            # this will be daily, but will be resampled later
            weight_ts = pd.date_range(start=earliest_date, end=latest_date)

            forecasts_weights = dict([
                (rule_variation_name, pd.Series(
                    [fixed_weights[rule_variation_name]] * len(weight_ts), index=weight_ts))
                for rule_variation_name in rule_variation_list])

            forecasts_weights = pd.concat(forecasts_weights, axis=1)
            forecasts_weights.columns = rule_variation_list

            return forecasts_weights

        forecast_weights = self.parent.calc_or_cache(
            "get_raw_forecast_weights", instrument_code, _get_raw_forecast_weights, self)
        return forecast_weights

    def get_forecast_weights(self, instrument_code):
        """
        Get the forecast weights

        We forward fill all forecasts. We then adjust forecast weights so that they are 1.0 in every
          period; after setting to zero when no forecast is available.

        :param instrument_code:
        :type str:

        :returns: TxK pd.DataFrame containing weights, columns are trading rule variation names, T covers all

        KEY OUTPUT

        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping()
        >>> system=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.combForecast.get_forecast_weights("EDOLLAR").tail(2)
                    ewmac16  ewmac8
        2015-12-10      0.5     0.5
        2015-12-11      0.5     0.5
        >>>
        >>> config.forecast_weights=dict(EDOLLAR=dict(ewmac8=0.9, ewmac16=0.1))
        >>> system2=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system2.combForecast.get_forecast_weights("EDOLLAR").tail(2)
                    ewmac16  ewmac8
        2015-12-10      0.1     0.9
        2015-12-11      0.1     0.9
        >>>
        >>> del(config.forecast_weights)
        >>> system3=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system3.combForecast.get_forecast_weights("EDOLLAR").tail(2)
        WARNING: No forecast weights  - using equal weights of 0.5000 over all 2 trading rules in system
                    ewmac16  ewmac8
        2015-12-10      0.5     0.5
        2015-12-11      0.5     0.5
        """
        def _get_forecast_weights(system, instrument_code, this_stage):

            forecast_weights = this_stage.get_raw_forecast_weights(
                instrument_code)
            rule_variation_list = list(forecast_weights.columns)
            forecasts = this_stage.get_all_forecasts(instrument_code, rule_variation_list)

            # adjust weights for missing data
            forecast_weights = fix_weights_vs_pdm(forecast_weights, forecasts)

            return forecast_weights

        forecast_weights = self.parent.calc_or_cache(
            'get_forecast_weights', instrument_code, _get_forecast_weights, self)
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
        2015-12-10  1.1
        2015-12-11  1.1
        >>>
        >>> config.forecast_div_multiplier=dict(EDOLLAR=2.0)
        >>> system2=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system2.combForecast.get_forecast_diversification_multiplier("EDOLLAR").tail(2)
                    fdm
        2015-12-10    2
        2015-12-11    2
        >>>
        >>> ## defaults
        >>> del(config.forecast_div_multiplier)
        >>> system3=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system3.combForecast.get_forecast_diversification_multiplier("EDOLLAR").tail(2)
                    fdm
        2015-12-10    1
        2015-12-11    1
        """
        def _get_forecast_div_multiplier(system, instrument_code, this_stage):

            # Let's try the config
            if hasattr(system.config, "forecast_div_multiplier"):
                if isinstance(system.config.forecast_div_multiplier, float):
                    fixed_div_mult = system.config.forecast_div_multiplier

                elif instrument_code in system.config.forecast_div_multiplier.keys():
                    # dict
                    fixed_div_mult = system.config.forecast_div_multiplier[
                        instrument_code]
                else:
                    raise Exception(
                        "FDM in config needs to be eithier float, or dict with instrument_code keys")

            elif "forecast_div_multiplier" in system_defaults:
                # try defaults
                fixed_div_mult = system_defaults['forecast_div_multiplier']
            else:
                raise Exception(
                    "Need to specify FDM in config or system_defaults")

            # Now we have a dict, fixed_weights.
            # Need to turn into a timeseries covering the range of forecast dates
            # get forecast weights first
            forecast_weights = this_stage.get_forecast_weights(instrument_code)
            weight_ts = forecast_weights.index

            ts_fdm = pd.Series([fixed_div_mult] *
                               len(weight_ts), index=weight_ts)
            ts_fdm = ts_fdm.to_frame("fdm")

            return ts_fdm

        forecast_div_multiplier = self.parent.calc_or_cache(
            'get_forecast_diversification_multiplier', instrument_code, _get_forecast_div_multiplier, self)
        return forecast_div_multiplier


    def get_combined_forecast(self, instrument_code):
        """
        Get a combined forecast, linear combination of individual forecasts with FDM applied

        We forward fill all forecasts. We then adjust forecast weights so that they are 1.0 in every
          period; after setting to zero when no forecast is available. Finally we multiply up, and
          apply the FDM. Then we cap.

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
        2015-12-10       1.619134
        2015-12-11       2.462610
        >>>
        >>> config.forecast_div_multiplier=1000.0
        >>> system2=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system2.combForecast.get_combined_forecast("EDOLLAR").tail(2)
                    comb_forecast
        2015-12-10             21
        2015-12-11             21
        """
        def _get_combined_forecast(system, instrument_code, this_stage):

            forecast_weights = this_stage.get_forecast_weights(instrument_code)
            rule_variation_list = list(forecast_weights.columns)

            forecasts = this_stage.get_all_forecasts(instrument_code, rule_variation_list)
            forecast_div_multiplier = this_stage.get_forecast_diversification_multiplier(
                instrument_code)
            forecast_cap = this_stage.get_forecast_cap()

            # multiply weights by forecasts
            combined_forecast = multiply_df(forecast_weights, forecasts)

            # sum
            combined_forecast = combined_forecast.sum(
                axis=1).to_frame("comb_forecast")

            # apply fdm
            # (note in this simple version we aren't adjusting FDM if forecast_weights change)
            forecast_div_multiplier = forecast_div_multiplier.reindex(
                forecasts.index, method="ffill")
            raw_combined_forecast = multiply_df(
                combined_forecast, forecast_div_multiplier)

            combined_forecast = apply_cap(raw_combined_forecast, forecast_cap)

            return combined_forecast

        combined_forecast = self.parent.calc_or_cache(
            'get_combined_forecast', instrument_code, _get_combined_forecast, self)
        return combined_forecast


class ForecastCombineEstimated(ForecastCombineFixed):
    """
    Stage for combining forecasts (already capped and scaled)
    
    Estimates forecast diversification multiplier

    Name: combForecast
    """
    def get_trading_rule_list(self, instrument_code):
        """
        Get list of all trading rule names
        
        If rule_variations is specified in config use that, otherwise use all available rules

        :param instrument_code:
        :type str:

        :returns: list of str

        KEY INPUT

        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping_estimate
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping_estimate()
        >>> system=System([rawdata, rules, fcs, ForecastCombineEstimated()], data, config)
        >>> system.combForecast.get_trading_rule_list("EDOLLAR")
        ['carry', 'ewmac16', 'ewmac8']
        >>> system.config.rule_variations=dict(EDOLLAR=["ewmac8"])
        >>> system.combForecast.get_trading_rule_list("EDOLLAR")
        ['ewmac8']
        """
        # Let's try the config
        system=self.parent

        if hasattr(system.config, "rule_variations"):
            ### 
            if instrument_code in system.config.rule_variations:
                # nested dict of lists
                rules = system.config.rule_variations[
                    instrument_code]
            else:
                # assume it's a non nested list
                rules = system.config.rule_variations
        else:
            ## not supplied in config
            rules = self.parent.rules.trading_rules().keys()
            
        rules = list(rules)
        rules.sort()

        return rules

    def _has_same_rules_as_code(self, instrument_code):
        """
        Returns all instruments with same set of trading rules as this one

        :param instrument_code:
        :type str:

        :returns: list of str


        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping_estimate
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping_estimate()
        >>> system=System([rawdata, rules, fcs, ForecastCombineEstimated()], data, config)
        >>> system.combForecast._has_same_rules_as_code("EDOLLAR")
        ['EDOLLAR', 'US10']
        >>> system.combForecast._has_same_rules_as_code("BUND")
        ['BUND']
        """
        
        my_rules=self.get_trading_rule_list(instrument_code)
        instrument_list=self.parent.get_instrument_list()
        
        def _matches(xlist, ylist):
            xlist.sort()
            ylist.sort()
            return xlist==ylist
        
        matching_instruments=[other_code for other_code in instrument_list 
                           if _matches(my_rules, self.get_trading_rule_list(other_code))]
        
        matching_instruments.sort()
        
        return matching_instruments

    def get_forecast_correlation_matrices(self, instrument_code):
        """
        Returns a correlationList object which contains a history of correlation matricies
        
        :param instrument_code:
        :type str:

        :returns: correlation_list object

        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping_estimate
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping_estimate()
        >>> system=System([rawdata, rules, fcs, ForecastCombineEstimated()], data, config)
        >>> ans=system.combForecast.get_forecast_correlation_matrices("EDOLLAR")
        >>> print(ans.corr_list[-1])
        [[ 1.          0.03850942  0.05401426]
         [ 0.03850942  1.          0.85892831]
         [ 0.05401426  0.85892831  1.        ]]
        >>> print(ans.columns)
        ['carry', 'ewmac16', 'ewmac8']
        """
        def _get_forecast_correlation_matrices(system, instrument_code, this_stage, 
                                               codes_to_use, corr_func, **corr_params):

            forecast_data=[this_stage.get_all_forecasts(code) for code in codes_to_use]
            forecast_data=[forecast_ts.ffill() for forecast_ts in forecast_data]

            if len(forecast_data)==1:
                ## not pooling use just one set of data
                forecast_data=forecast_data[0]
                
            return corr_func(forecast_data, **corr_params)
                            
        ## Get some useful stuff from the config
        corr_params=self.parent.config.dict_with_defaults("forecast_correlation_estimate", 
             ['func', 'pool_instruments', 'frequency', 'date_method', 'using_exponent',
              'ew_lookback','min_periods','cleaning'])

        ## do we pool our estimation?
        pooling=str2Bool(corr_params.pop("pool_instruments"))
        
        ## which function to use for calculation
        corr_func=resolve_function(corr_params.pop("func"))
        
        if pooling:
            ## find set of instruments with same trading rules as I have
            codes_to_use=self._has_same_rules_as_code(instrument_code)
            instrument_code_ref=ALL_KEYNAME
            
            ## We 
            label='get_forecast_correlation_matrices'+'_'.join(codes_to_use)
            
        else:

            codes_to_use=[instrument_code]
            label='get_forecast_correlation_matrices'
            instrument_code_ref=instrument_code
        ##
        ## label: how we identify this thing in the cache
        ## instrument_code_ref: eithier the instrument code, or 'all markets' if pooling
        ## _get_forecast_correlation_matrices: function to call if we don't find in cache
        ## self: this_system stage object
        ## codes_to_use: instrument codes 
        ## func: function to call to calculate correlations
        ## **corr_params: parameters to pass to correlation function
        ##
        forecast_corr_list = self.parent.calc_or_cache(
            label, instrument_code_ref, _get_forecast_correlation_matrices,
             self, codes_to_use, corr_func, **corr_params)
        
        return forecast_corr_list






if __name__ == '__main__':
    import doctest
    doctest.testmod()
