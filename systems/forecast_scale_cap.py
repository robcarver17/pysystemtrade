from copy import copy

import pandas as pd

from systems.basesystem import ALL_KEYNAME
from systems.stage import SystemStage
from systems.defaults import system_defaults

from syscore.genutils import str2Bool
from syscore.pdutils import apply_cap
from syscore.objects import resolve_function

FCAST_SCALE_CAP_STAGE_NAME = "forecastScaleCap"

class ForecastScaleCap(SystemStage):
    """
    Stage for scaling and capping

    This is a 'switching' class which selects either the fixed or the
      estimated flavours

    """

    def _name(self):
        return FCAST_SCALE_CAP_STAGE_NAME

    def _description(self):
        return "unswitched"


    def _system_init(self, system):
        """
        When we add this stage object to a system, this code will be run

        It will determine if we use an estimate or a fixed class of object
        """
        super()._system_init(system)

        if str2Bool(system.config.use_forecast_scale_estimates):
            fixed_flavour = False
        else:
            fixed_flavour = True

        if fixed_flavour:
            self.__class__ = ForecastScaleCapFixed
            self.__init__()
            setattr(self, "parent", system)

        else:
            self.__class__ = ForecastScaleCapEstimated
            self.__init__()
            setattr(self, "parent", system)


class BaseForecastScaleCap(SystemStage):
    def __init__(self):

        super().__init__()


        protected = ["get_forecast_scalars"]
        setattr(self, "_protected", protected)

    def _description(self):
        return "base_do_not_use"

    def _name(self):
        return FCAST_SCALE_CAP_STAGE_NAME

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
        2015-12-10 -0.035959
        2015-12-11  0.164383
        """

        raw_forecast = self.parent.rules.get_raw_forecast(
            instrument_code, rule_variation_name)

        return raw_forecast

    def get_forecast_cap(self):
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

        def _get_forecast_cap(system, not_used, this_stage_not_used):
            # Try the config file else defaults

            return system.config.forecast_cap

        forecast_cap = self.parent.calc_or_cache(
            "get_forecast_cap", ALL_KEYNAME, _get_forecast_cap, self)

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
        2015-12-10 -0.190583
        2015-12-11  0.871231
        """

        def _get_scaled_forecast(
                system, instrument_code, rule_variation_name, this_stage):

            raw_forecast = this_stage.get_raw_forecast(
                instrument_code, rule_variation_name)
            scale = this_stage.get_forecast_scalar(
                instrument_code, rule_variation_name)

            if isinstance(scale, float):
                scaled_forecast = raw_forecast * scale
            else:
                # time series
                scaled_forecast = raw_forecast * scale

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
        2015-12-10 -0.190583
        2015-12-11  0.200000
        """

        def _get_capped_forecast(
                system, instrument_code, rule_variation_name, this_stage):

            this_stage.log.msg("Calculating capped forecast for %s %s" % (instrument_code, rule_variation_name),
                               instrument_code=instrument_code, rule_variation_name=rule_variation_name)

            scaled_forecast = this_stage.get_scaled_forecast(
                instrument_code, rule_variation_name)
            cap = this_stage.get_forecast_cap()

            capped_forecast = apply_cap(scaled_forecast, cap)

            return capped_forecast

        capped_forecast = self.parent.calc_or_cache_nested(
            "get_capped_forecast", instrument_code, rule_variation_name, _get_capped_forecast, self)

        return capped_forecast


class ForecastScaleCapFixed(BaseForecastScaleCap):
    """
    Create a SystemStage for scaling and capping forecasting

    This simple variation uses Fixed capping and scaling

    KEY INPUT: system.rules.get_raw_forecast(instrument_code, rule_variation_name)
                found in self.get_raw_forecast(instrument_code, rule_variation_name)

    KEY OUTPUT: system.forecastScaleCap.get_capped_forecast(instrument_code, rule_variation_name)

                system.forecastScaleCap.get_forecast_cap()

    Name: forecastScaleCap
    """


    def _description(self):
        return "fixed"


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


class ForecastScaleCapEstimated(BaseForecastScaleCap):
    """
    This variation will estimate the scaling parameter

    See the base class for inputs, outputs, etc

    Name: forecastScaleCap
    """


    def _description(self):
        return "Estimated"

    def get_forecast_scalar(self, instrument_code, rule_variation_name):
        """
        Get the scalar to apply to raw forecasts

        If not cached, these are estimated from past forecasts

        If configuration variable pool_forecasts_for_scalar is "True", then we
          do this across instruments.

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
        2015-12-09      5.849888
        2015-12-10      5.850474
        2015-12-11      5.851091
        >>> system1.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac8").tail(3)
                      ewmac8
        2015-12-09  0.645585
        2015-12-10 -0.210377
        2015-12-11  0.961821
        >>>
        >>> ## From config
        >>> scale_config=dict(pool_instruments=False)
        >>> config.forecast_scalar_estimate=scale_config
        >>> system3=System([rawdata, rules, ForecastScaleCapEstimated()], data, config)
        >>> system3.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8").tail(3)
                    scale_factor
        2015-12-09      5.652174
        2015-12-10      5.652833
        2015-12-11      5.653444
        >>>
        """

        def _get_forecast_scalar(system, Not_Used, rule_variation_name,
                                 this_stage, instrument_list, scalar_function,
                                 forecast_scalar_config):
            """
            instrument_list contains multiple things, pools everything across
              all instruments
            """
            this_stage.log.msg("Getting forecast scalar for %s over %s" % (rule_variation_name, ", ".join(instrument_list)),
                               rule_variation_name=rule_variation_name)
            # Get forecasts for each instrument
            forecast_list = [
                this_stage.get_raw_forecast(
                    instrument_code, rule_variation_name)
                for instrument_code in instrument_list]

            cs_forecasts = pd.concat(forecast_list, axis=1)

            scaling_factor = scalar_function(
                cs_forecasts, **forecast_scalar_config)

            return scaling_factor

        # Get some useful stuff from the config
        forecast_scalar_config = copy(
            self.parent.config.forecast_scalar_estimate)

        # The config contains 'func' and some other arguments
        # we turn func which could be a string into a function, and then
        # call it with the other ags
        scalarfunction = resolve_function(forecast_scalar_config.pop('func'))

        # this determines whether we pool or not
        pool_instruments = str2Bool(
            forecast_scalar_config.pop("pool_instruments"))

        if pool_instruments:
            # pooled, same for all instruments
            instrument_code_key = ALL_KEYNAME
            instrument_list = self.parent.get_instrument_list()

        else:
            ## not pooled
            instrument_code_key = instrument_code
            instrument_list = [instrument_code]

        forecast_scalar = self.parent.calc_or_cache_nested(
            "get_forecast_scalar", instrument_code_key, rule_variation_name,
            _get_forecast_scalar, self, instrument_list, scalarfunction, forecast_scalar_config)

        return forecast_scalar


if __name__ == '__main__':
    import doctest
    doctest.testmod()
