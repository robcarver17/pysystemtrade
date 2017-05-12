from copy import copy

import pandas as pd

from systems.basesystem import ALL_KEYNAME
from systems.stage import SystemStage
from systems.defaults import system_defaults
from systems.system_cache import input, dont_cache, diagnostic, output

from syscore.genutils import str2Bool
from syscore.pdutils import apply_cap
from syscore.objects import resolve_function


class ForecastScaleCap(SystemStage):
    """
    Stage for scaling and capping

    This is a 'switching' class which selects either the fixed or the
      estimated flavours

    """

    def _name(self):
        return "forecastScaleCap"

    @input
    def get_raw_forecast(self, instrument_code, rule_variation_name):
        """
        Convenience method as we use the raw forecast several times

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

    @diagnostic()
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

        return self.parent.config.forecast_cap

    @dont_cache
    def _use_fixed_weights(self):
        if str2Bool(self.parent.config.use_forecast_scale_estimates):
            fixed_flavour = True
        else:
            fixed_flavour = False

        return fixed_flavour

    @diagnostic()
    def _get_forecast_scalar_fixed(self, instrument_code, rule_variation_name):
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

        system = self.parent
        try:
            scalar = system.config.trading_rules[rule_variation_name][
                'forecast_scalar']
        except:
            try:
                # can also put somewhere else ...
                scalar = system.config.forecast_scalars[rule_variation_name]
            except:
                # go with defaults
                scalar = system_defaults['forecast_scalar']

        return scalar

    # protected in cache as slow to estimate
    @diagnostic(protected=True)
    def _get_forecast_scalar_estimated_from_instrument_list(
            self, instrument_code, rule_variation_name,
            forecast_scalar_config):
        """
        Get the scalar to apply to raw forecasts

        If not cached, these are estimated from past forecasts


        :param instrument_code: instrument code, or ALL_KEYNAME if pooling
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :param forecast_scalar_config:
        :type dict: relevant part of the config

        :returns: float

        """

        # The config contains 'func' and some other arguments
        # we turn func which could be a string into a function, and then
        # call it with the other ags
        scalar_function = resolve_function(forecast_scalar_config.pop('func'))
        """
        instrument_list contains multiple things, might pool everything across
          all instruments
        """

        if instrument_code == ALL_KEYNAME:
            # pooled, same for all instruments
            instrument_list = self.parent.get_instrument_list()

        else:
            ## not pooled
            instrument_list = [instrument_code]

        self.log.msg(
            "Getting forecast scalar for %s over %s" %
            (rule_variation_name, ", ".join(instrument_list)),
            rule_variation_name=rule_variation_name)

        # Get forecasts for each instrument
        forecast_list = [
            self.get_raw_forecast(instrument_code, rule_variation_name)
            for instrument_code in instrument_list
        ]

        cs_forecasts = pd.concat(forecast_list, axis=1)

        # an example of a scaling function is syscore.algos.forecast_scalar
        # must return thing the same size as cs_forecasts
        scaling_factor = scalar_function(cs_forecasts,
                                         **forecast_scalar_config)

        return scaling_factor

    # protected in cache as slow to estimate
    @diagnostic(protected=True)
    def _get_forecast_scalar_estimated(self, instrument_code,
                                       rule_variation_name):
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
        # Get some useful stuff from the config
        forecast_scalar_config = copy(
            self.parent.config.forecast_scalar_estimate)

        # this determines whether we pool or not
        pool_instruments = str2Bool(
            forecast_scalar_config.pop("pool_instruments"))

        if pool_instruments:
            # pooled, same for all instruments
            instrument_code_to_pass = ALL_KEYNAME
        else:
            instrument_code_to_pass = copy(instrument_code)

        scaling_factor = self._get_forecast_scalar_estimated_from_instrument_list(
            instrument_code_to_pass, rule_variation_name,
            forecast_scalar_config)
        forecast = self.get_raw_forecast(instrument_code, rule_variation_name)

        scaling_factor = scaling_factor.reindex(forecast.index, method="ffill")

        return scaling_factor

    @dont_cache
    def _use_estimated_weights(self):
        return str2Bool(self.parent.config.use_forecast_scale_estimates)

    @dont_cache
    def get_forecast_scalar(self, instrument_code, rule_variation_name):
        if self._use_estimated_weights():
            return self._get_forecast_scalar_estimated(instrument_code,
                                                       rule_variation_name)
        else:
            return self._get_forecast_scalar_fixed(instrument_code,
                                                   rule_variation_name)

    @diagnostic()
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

        raw_forecast = self.get_raw_forecast(instrument_code,
                                             rule_variation_name)
        scale = self.get_forecast_scalar(
            instrument_code,
            rule_variation_name)  ## will eithier be a scalar or a timeseries

        scaled_forecast = raw_forecast * scale

        return scaled_forecast

    @output()
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

        self.log.msg(
            "Calculating capped forecast for %s %s" % (instrument_code,
                                                       rule_variation_name),
            instrument_code=instrument_code,
            rule_variation_name=rule_variation_name)

        scaled_forecast = self.get_scaled_forecast(instrument_code,
                                                   rule_variation_name)
        cap = self.get_forecast_cap()

        capped_forecast = apply_cap(scaled_forecast, cap)

        return capped_forecast


if __name__ == '__main__':
    import doctest
    doctest.testmod()
