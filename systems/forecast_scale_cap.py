
from systems.stage import SystemStage
from systems.defaults import system_defaults
from syscore.pdutils import apply_cap


class ForecastScaleCapFixed(SystemStage):
    """
    Create a SystemStage for scaling and capping forecasting

    This simple variation uses Fixed capping and scaling

    KEY INPUT: system.rules.get_raw_forecast(instrument_code, rule_variation_name)
                found in self.get_raw_forecast(instrument_code, rule_variation_name)

    KEY OUTPUT: system.forecastScaleCap.get_capped_forecast(instrument_code, rule_variation_name)

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
        2015-04-21  1.082781
        2015-04-22  0.954941
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

        return forecast_scalar

    def get_forecast_cap(self, instrument_code, rule_variation_name):
        """
        Get forecast cap

        In this simple version it's the same for all instruments, and rule variations

        We get the cap from:
                                 (a)  configuration object in parent system
                                 (c) or if missing: uses the forecast_cap from systems.default.py

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: float

        >>> from systems.tests.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>>
        >>> ## From config
        >>> system.forecastScaleCap.get_forecast_cap("EDOLLAR", "ewmac8")
        21.0
        >>>
        >>> ## default
        >>> del(config.forecast_cap)
        >>> system3=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system3.forecastScaleCap.get_forecast_cap("EDOLLAR", "ewmac8")
        20.0

        """

        def _get_forecast_cap(system, instrument_code,
                              rule_variation_name, this_stage):
            # Try the config file
            try:
                cap = system.config.forecast_cap
            except:
                # go with defaults
                cap = system_defaults['forecast_cap']

            return cap

        forecast_cap = self.parent.calc_or_cache_nested(
            "get_forecast_cap", instrument_code, rule_variation_name, _get_forecast_cap, self)

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
        2015-04-21  5.738741
        2015-04-22  5.061187
        """

        def _get_scaled_forecast(
                system, instrument_code, rule_variation_name, this_stage):
            raw_forecast = this_stage.get_raw_forecast(
                instrument_code, rule_variation_name)
            scale = this_stage.get_forecast_scalar(
                instrument_code, rule_variation_name)

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
        >>> config.forecast_cap=4.0
        >>> system=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac8").tail(2)
                    ewmac8
        2015-04-21       4
        2015-04-22       4


        """

        def _get_capped_forecast(
                system, instrument_code, rule_variation_name, this_stage):

            scaled_forecast = this_stage.get_scaled_forecast(
                instrument_code, rule_variation_name)
            cap = this_stage.get_forecast_cap(
                instrument_code, rule_variation_name)

            capped_forecast = apply_cap(scaled_forecast, cap)
            capped_forecast.columns = scaled_forecast.columns

            return capped_forecast

        capped_forecast = self.parent.calc_or_cache_nested(
            "get_capped_forecast", instrument_code, rule_variation_name, _get_capped_forecast, self)

        return capped_forecast


if __name__ == '__main__':
    import doctest
    doctest.testmod()
