from copy import copy

import numpy as np
import pandas as pd

from sysdata.config.configdata import Config

from systems.basesystem import ALL_KEYNAME
from systems.stage import SystemStage
from systems.system_cache import input, dont_cache, diagnostic, output

from syscore.genutils import str2Bool
from syscore.objects import resolve_function


class ForecastScaleCap(SystemStage):
    """
    Stage for scaling and capping

    This is a 'switching' class which selects either the fixed or the
      estimated flavours

    """

    @property
    def name(self):
        return "forecastScaleCap"

    @output()
    def get_capped_forecast(
        self, instrument_code: str, rule_variation_name: str
    ) -> pd.Series:
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

        self.log.debug(
            "Calculating capped forecast for %s %s"
            % (instrument_code, rule_variation_name),
            instrument_code=instrument_code,
        )

        scaled_forecast = self.get_scaled_forecast(instrument_code, rule_variation_name)
        upper_cap = self.get_forecast_cap()
        lower_floor = self.get_forecast_floor()

        capped_scaled_forecast = scaled_forecast.clip(
            upper=upper_cap, lower=lower_floor
        )

        return capped_scaled_forecast

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

        raw_forecast = self.get_raw_forecast(instrument_code, rule_variation_name)
        forecast_scalar = self.get_forecast_scalar(
            instrument_code, rule_variation_name
        )  # will either be a scalar or a timeseries

        scaled_forecast = raw_forecast * forecast_scalar

        return scaled_forecast

    @input
    def get_raw_forecast(
        self, instrument_code: str, rule_variation_name: str
    ) -> pd.Series:
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

        raw_forecast = self.rules_stage.get_raw_forecast(
            instrument_code, rule_variation_name
        )

        return raw_forecast

    @property
    def rules_stage(self):
        return self.parent.rules

    @dont_cache
    def get_forecast_scalar(
        self, instrument_code: str, rule_variation_name: str
    ) -> pd.Series:
        if self._use_estimated_weights():
            forecast_scalar = self._get_forecast_scalar_estimated(
                instrument_code, rule_variation_name
            )
        else:
            forecast_scalar = self._get_forecast_scalar_fixed_as_series(
                instrument_code, rule_variation_name
            )

        return forecast_scalar

    @dont_cache
    def _use_estimated_weights(self) -> bool:
        return str2Bool(self.config.use_forecast_scale_estimates)

    @property
    def config(self) -> Config:
        return self.parent.config

    # protected in cache as slow to estimate
    @diagnostic(protected=True)
    def _get_forecast_scalar_estimated(
        self, instrument_code: str, rule_variation_name: str
    ) -> pd.Series:
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
        forecast_scalar_config = copy(self.config.forecast_scalar_estimate)

        instrument_code_to_pass = _get_instrument_code_depending_on_pooling_status(
            instrument_code=instrument_code,
            forecast_scalar_config=forecast_scalar_config,
        )

        scaling_factor = self._get_forecast_scalar_estimated_from_instrument_code(
            instrument_code=instrument_code_to_pass,
            rule_variation_name=rule_variation_name,
            forecast_scalar_config=forecast_scalar_config,
        )

        forecast = self.get_raw_forecast(instrument_code, rule_variation_name)
        forecast_scalar = scaling_factor.reindex(forecast.index, method="ffill")

        return forecast_scalar

    # protected in cache as slow to estimate
    @diagnostic(protected=True)
    def _get_forecast_scalar_estimated_from_instrument_code(
        self,
        instrument_code: str,
        rule_variation_name: str,
        forecast_scalar_config: dict,
    ) -> pd.Series:
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
        # call it with the other args

        cs_forecasts = self._get_cross_sectional_forecasts_for_instrument(
            instrument_code, rule_variation_name
        )
        scalar_function = resolve_function(forecast_scalar_config.pop("func"))

        # an example of a scaling function is sysquant.estimators.forecast_scalar.forecast_scalar
        # must return thing the same size as cs_forecasts

        # This we get from here to avoid possible inconsistency
        target_abs_forecast = self.target_abs_forecast()

        scaling_factor = scalar_function(
            cs_forecasts,
            target_abs_forecast=target_abs_forecast,
            **forecast_scalar_config,
        )

        return scaling_factor

    @dont_cache
    def target_abs_forecast(self) -> float:
        return self.config.average_absolute_forecast

    @diagnostic()
    def _get_cross_sectional_forecasts_for_instrument(
        self, instrument_code: str, rule_variation_name: str
    ) -> pd.DataFrame:
        """
        instrument_list contains multiple things, might pool everything across
          all instruments
        """

        if instrument_code == ALL_KEYNAME:
            # pool data across all instruments using this trading rule
            instrument_list = self._list_of_instruments_for_trading_rule(
                rule_variation_name
            )

        else:
            ## not pooled
            instrument_list = [instrument_code]

        self.log.debug(
            "Getting cross sectional forecasts for scalar calculation for %s over %s"
            % (rule_variation_name, ", ".join(instrument_list))
        )

        forecast_list = [
            self.get_raw_forecast(instrument_code, rule_variation_name)
            for instrument_code in instrument_list
        ]

        cs_forecasts = pd.concat(forecast_list, axis=1)
        cs_forecasts.columns = instrument_list

        return cs_forecasts

    @diagnostic()
    def _list_of_instruments_for_trading_rule(self, rule_variation_name: str) -> list:
        """
        Return the list of instruments associated with a given rule

        If we don't have a combForecast this will be all of our instruments

        :param rule_variation_name:
        :return: list
        """

        instrument_list = self.parent.get_instrument_list()
        instruments_with_rule = [
            instrument_code
            for instrument_code in instrument_list
            if rule_variation_name in self._get_trading_rule_list(instrument_code)
        ]

        if len(instruments_with_rule) == 0:
            return instrument_list
        else:
            return instruments_with_rule

    @input
    def _get_trading_rule_list(self, instrument_code: str) -> list:
        """
        Get a list of trading rules which apply to a particular instrument

        :param instrument_code:
        :return: list of trading rules
        """

        try:
            getattr(self.parent, "combForecast")
        except AttributeError:
            return []
        else:
            return self.comb_forecast_stage.get_trading_rule_list(instrument_code)

    @property
    def comb_forecast_stage(self):
        # no use of -> as would cause circular import
        return self.parent.combForecast

    @diagnostic()
    def _get_forecast_scalar_fixed_as_series(
        self, instrument_code: str, rule_variation_name: str
    ) -> pd.Series:
        """
        Get the scalar to apply to raw forecasts

        In this simple version it's the same for all instruments, and fixed

        We get the scalars from: (a) configuration file in parent system
                                 (b) or if missing: uses the scalar from systems.defaults.py

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str: name of the trading rule variation

        :returns: Series

        """
        scalar = self._get_forecast_scalar_fixed(
            instrument_code=instrument_code, rule_variation_name=rule_variation_name
        )
        raw_forecast = self.get_raw_forecast(
            instrument_code=instrument_code, rule_variation_name=rule_variation_name
        )
        forecast_scalar = pd.Series(
            np.full(raw_forecast.shape[0], scalar), index=raw_forecast.index
        )

        return forecast_scalar

    @diagnostic()
    def _get_forecast_scalar_fixed(
        self, instrument_code: str, rule_variation_name: str
    ) -> pd.Series:
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

        config = self.config
        try:
            scalar = config.trading_rules[rule_variation_name]["forecast_scalar"]
        except:
            try:
                # can also put somewhere else ...
                scalar = config.forecast_scalars[rule_variation_name]
            except:
                # just one global default
                scalar = config.get_element("forecast_scalar")

        return scalar

    @diagnostic()
    def get_forecast_cap(self) -> float:
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

        return self.config.forecast_cap

    @diagnostic()
    def get_forecast_floor(self) -> float:
        """
        Get forecast floor

        We get the cap from:
                                 (a)  configuration object in parent system
                                 (c) or if missing: uses the the cap with a minus sign in front of it
        :returns: float

        """

        forecast_cap = self.get_forecast_cap()
        minus_forecast_cap = -forecast_cap
        forecast_floor = getattr(self.config, "forecast_floor", minus_forecast_cap)

        return forecast_floor


def _get_instrument_code_depending_on_pooling_status(
    instrument_code: str, forecast_scalar_config: dict
) -> str:
    # this determines whether we pool or not
    pool_instruments = str2Bool(forecast_scalar_config.pop("pool_instruments"))

    if pool_instruments:
        # pooled, same for all instruments
        instrument_code_to_pass = ALL_KEYNAME
    else:
        instrument_code_to_pass = copy(instrument_code)

    return instrument_code_to_pass


if __name__ == "__main__":
    import doctest

    doctest.testmod()
