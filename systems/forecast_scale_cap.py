from copy import copy

import pandas as pd

from systems.basesystem import ALL_KEYNAME
from systems.stage import SystemStage
from systems.defaults import system_defaults
from syscore.pdutils import apply_cap, multiply_df_single_column
from syscore.objects import resolve_function

class ForecastScaleCapFixed(SystemStage):
    """
    Create a SystemStage for scaling and capping forecasting

    This simple variation uses Fixed capping and scaling

    KEY INPUT: system.rules.get_raw_forecast(instrument_code, rule_variation_name)
                found in self.get_raw_forecast(instrument_code, rule_variation_name)

    KEY OUTPUT: system.forecastScaleCap.get_capped_forecast(instrument_code, rule_variation_name)

                system.forecastScaleCap.get_forecast_cap()

    Name: forecastScaleCap
    """

    def __init__(self):
        """
        Create a SystemStage for scaling and capping forecasting

        Using Fixed capping and scaling

        :returns: None

        """

        protected = ["get_forecast_scalars"]
        setattr(self, "_protected", protected)

        setattr(self, "name", "forecastScaleCap")

    def get_raw_forecast(self, instrument_code, rule_variation_name):
        """
        Convenience method as we use the raw forecast several times

        KEY_INPUT

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: Tx1 pd.DataFrame, same size as forecast

        >>> from systems.tests.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system.forecastScaleCap.get_raw_forecast("EDOLLAR","ewmac8").tail(2)
                      ewmac8
        2015-12-10 -0.046088
        2015-12-11  0.029377
        """

        raw_forecast = self.parent.rules.get_raw_forecast(
            instrument_code, rule_variation_name)

        return raw_forecast

    def get_forecast_scalar(self, instrument_code, rule_variation_name):
        """
        Get the scalar to apply to raw forecasts

        In this simple version it's the same for all instruments, and fixed

        We get the scalars from: (a) configuration file in parent system
                                 (b) or if missing: uses the scalar from systems.defaults.py

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: float

        >>> from systems.tests.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system1=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>>
        >>> ## From config
        >>> system1.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8")
        5.3
        >>>
        >>> ## default
        >>> unused=config.trading_rules['ewmac8'].pop('forecast_scalar')
        >>> system3=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system3.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8")
        1.0
        >>>
        >>> ## other config location
        >>> setattr(config, 'forecast_scalars', dict(ewmac8=11.0))
        >>> system4=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system4.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8")
        11.0
        """

        def _get_forecast_scalar(
                system, instrument_code, rule_variation_name, this_stage):
            # Try the config file
            try:
                scalar = system.config.trading_rules[
                    rule_variation_name]['forecast_scalar']
            except:
                try:
                    # can also put somewhere else ...
                    scalar = system.config.forecast_scalars[
                        rule_variation_name]
                except:
                    # go with defaults
                    scalar = system_defaults['forecast_scalar']

            return scalar

        forecast_scalar = self.parent.calc_or_cache_nested(
            "get_forecast_scalar", instrument_code, rule_variation_name, _get_forecast_scalar, self)

        return float(forecast_scalar)

    def get_forecast_cap(self,):
        """
        Get forecast cap

        We get the cap from:
                                 (a)  configuration object in parent system
                                 (c) or if missing: uses the forecast_cap from systems.default.py
        :returns: float

        >>> from systems.tests.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>>
        >>> ## From config
        >>> system.forecastScaleCap.get_forecast_cap()
        21.0
        >>>
        >>> ## default
        >>> del(config.forecast_cap)
        >>> system3=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system3.forecastScaleCap.get_forecast_cap()
        20.0

        """

        def _get_forecast_cap(system, not_used):
            # Try the config file
            try:
                cap = system.config.forecast_cap
            except:
                # go with defaults
                cap = system_defaults['forecast_cap']

            return cap

        forecast_cap = self.parent.calc_or_cache(
            "get_forecast_cap", ALL_KEYNAME, _get_forecast_cap)

        return forecast_cap

    def get_scaled_forecast(self, instrument_code, rule_variation_name):
        """
        Return the scaled forecast

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: Tx1 pd.DataFrame, same size as forecast

        >>> from systems.tests.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system.forecastScaleCap.get_scaled_forecast("EDOLLAR", "ewmac8").tail(2)
                      ewmac8
        2015-12-10 -0.244268
        2015-12-11  0.155697
        """

        def _get_scaled_forecast(
                system, instrument_code, rule_variation_name, this_stage):
            raw_forecast = this_stage.get_raw_forecast(
                instrument_code, rule_variation_name)
            scale = this_stage.get_forecast_scalar(
                instrument_code, rule_variation_name)

            if type(scale) is float:
                scaled_forecast = raw_forecast * scale
            else: 
                ## time series
                scaled_forecast = multiply_df_single_column(raw_forecast, scale, ffill=(False,True))

            return scaled_forecast

        scaled_forecast = self.parent.calc_or_cache_nested(
            "get_scaled_forecast", instrument_code, rule_variation_name, _get_scaled_forecast, self)

        return scaled_forecast

    def get_capped_forecast(self, instrument_code, rule_variation_name):
        """

        Return the capped, scaled,  forecast

        KEY OUTPUT


        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: Tx1 pd.DataFrame, same size as forecast

        >>> from systems.tests.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> config.forecast_cap=0.2
        >>> system=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac8").tail(2)
                      ewmac8
        2015-12-10 -0.200000
        2015-12-11  0.155697


        """

        def _get_capped_forecast(
                system, instrument_code, rule_variation_name, this_stage):

            scaled_forecast = this_stage.get_scaled_forecast(
                instrument_code, rule_variation_name)
            cap = this_stage.get_forecast_cap()

            capped_forecast = apply_cap(scaled_forecast, cap)
            capped_forecast.columns = scaled_forecast.columns

            return capped_forecast

        capped_forecast = self.parent.calc_or_cache_nested(
            "get_capped_forecast", instrument_code, rule_variation_name, _get_capped_forecast, self)

        return capped_forecast


class ForecastScaleCapEstimated(ForecastScaleCapFixed):
    """
    This variation will estimate the scaling parameter

    See the base class for inputs, outputs, etc

    Name: forecastScaleCap
    """


    def get_forecast_scalar(self, instrument_code, rule_variation_name):
        """
        Get the scalar to apply to raw forecasts

        If not cached, these are estimated from past forecasts
        
        If configuration variable pool_forecasts_for_scalar is "True", then we do this across instruments.
        
        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: float

        >>> from systems.tests.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system1=System([rawdata, rules, ForecastScaleCapEstimated()], data, config)
        >>>
        >>> ## From default
        >>> system1.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8").tail(3)
                    scale_factor
        2015-12-09      9.557415
        2015-12-10      9.558276
        2015-12-11      9.559214
        >>> system1.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac8").tail(3)
                      ewmac8
        2015-12-09 -0.040374
        2015-12-10 -0.440524
        2015-12-11  0.280819
        >>>
        >>> ## From config
        >>> scale_config=dict(pool_instruments=False, func="syscore.algos.forecast_scalar")
        >>> config.forecast_scalar_estimate=scale_config
        >>> system3=System([rawdata, rules, ForecastScaleCapEstimated()], data, config)
        >>> system3.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8").tail(3)
                    scale_factor
        2015-12-09     10.635123
        2015-12-10     10.637808
        2015-12-11     10.640495
        >>>
        """

        def _get_forecast_scalar_pooled(
                system, Not_Used, rule_variation_name, this_stage, 
                scalar_function, forecast_scalar_config):
            """
            Pools everything across all instruments
            """
            instrument_list=system.get_instrument_list()
            
            ## Get forecasts for each instrument
            forecast_list=[
                   this_stage.get_raw_forecast(instrument_code, rule_variation_name) 
                   for instrument_code in instrument_list]
            
            cs_forecasts=pd.concat(forecast_list, axis=1)
            
            scaling_factor=scalar_function(cs_forecasts, **forecast_scalar_config)
            
            return scaling_factor

        def _get_forecast_scalar_instrument(
                system, instrument_code, rule_variation_name, this_stage,
                scalar_function, forecast_scalar_config):
            """
            Estimate only for this instrument
            """
            raw_forecast=this_stage.get_raw_forecast(instrument_code, rule_variation_name)
            scaling_factor=scalar_function(raw_forecast, **forecast_scalar_config)
            
            return scaling_factor

        ## Get some useful stuff from the config
        forecast_scalar_config=getattr(self.parent.config, "forecast_scalar_estimate", system_defaults["forecast_scalar_estimate"])
        forecast_scalar_config=copy(forecast_scalar_config)

        if "func" not in forecast_scalar_config or "pool_instruments" not in forecast_scalar_config:

            raise Exception(
                "The forecast_scalar_estimate config dict needs to have 'func' and 'pool_instruments' keys")

        # The config contains 'func' and some other arguments
        # we turn func which could be a string into a function, and then
        # call it with the other ags
        scalarfunction = resolve_function(forecast_scalar_config.pop('func'))

        ## this determines whether we pool or not        
        pool_instruments=bool(forecast_scalar_config.pop("pool_instruments"))

        if pool_instruments:
            ## pooled, same for all instruments
            forecast_scalar = self.parent.calc_or_cache_nested(
                "get_forecast_scalar", ALL_KEYNAME, rule_variation_name, 
                _get_forecast_scalar_pooled, self, scalarfunction, forecast_scalar_config)
            
        else:
            ## not pooled
            forecast_scalar = self.parent.calc_or_cache_nested(
                "get_forecast_scalar", instrument_code, rule_variation_name, 
                _get_forecast_scalar_instrument, self,  scalarfunction, forecast_scalar_config)


        return forecast_scalar



if __name__ == '__main__':
    import doctest
    doctest.testmod()
