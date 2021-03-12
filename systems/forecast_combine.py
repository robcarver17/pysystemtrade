from copy import copy

import pandas as pd

from syscore.genutils import str2Bool
from syscore.objects import resolve_function, missing_data
from syscore.pdutils import dataframe_pad, fix_weights_vs_position_or_forecast, from_dict_of_values_to_df, from_scalar_values_to_ts
from syscore.algos import map_forecast_value
from sysdata.config.defaults import get_default_config_key_value
from systems.stage import SystemStage
from systems.system_cache import diagnostic, dont_cache, input, output


class ForecastCombine(SystemStage
):
    """
    Stage for combining forecasts (already capped and scaled)
    """

    @property
    def name(self):
        return "combForecast"


    @output()
    def get_combined_forecast(self, instrument_code: str) -> pd.Series:
        """
        Get a combined forecast, linear combination of individual forecasts
        with FDM applied

        We forward fill all forecasts. We then adjust forecast weights so that
          they are 1.0 in every period; after setting to zero when no forecast
          is available. Finally we multiply up, and apply the FDM. Then we cap.

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
        self.log.msg(
            "Calculating combined forecast for %s" % (instrument_code),
            instrument_code=instrument_code,
        )
        raw_multiplied_combined_forecast = self.get_raw_combined_forecast_before_mapping(
            instrument_code
        )

        # apply cap and /or any non linear mapping
        (
            mapping_and_capping_function,
            mapping_and_capping_kwargs,
        ) = self._get_forecast_mapping_function(instrument_code)

        combined_forecast = mapping_and_capping_function(
            raw_multiplied_combined_forecast, **mapping_and_capping_kwargs
        )

        return combined_forecast

    # FORECAST = AGGREGATE SUM OF FORECASTS * IDM
    @diagnostic()
    def get_raw_combined_forecast_before_mapping(self, instrument_code: str) -> pd.Series:

        # sum
        raw_combined_forecast = self.get_combined_forecast_without_multiplier(instrument_code)

        forecast_div_multiplier = self.get_monthly_forecast_diversification_multiplier(
            instrument_code
        )

        forecast_div_multiplier = forecast_div_multiplier.reindex(raw_combined_forecast.index).ffill()

        # apply fdm
        raw_multiplied_combined_forecast = (
            raw_combined_forecast * forecast_div_multiplier.ffill()
        )

        return raw_multiplied_combined_forecast

    @diagnostic()
    def get_combined_forecast_without_multiplier(self, instrument_code: str) -> pd.Series:
        # We take our list of rule variations from the forecasts, since it
        # might be that some rules were omitted in the weight calculation

        weighted_forecasts = self.get_weighted_forecasts_without_multiplier(instrument_code)

        # sum
        raw_combined_forecast = weighted_forecasts.sum(axis=1)

        return raw_combined_forecast

    @diagnostic()
    def get_weighted_forecasts_without_multiplier(self, instrument_code: str) -> pd.DataFrame:
        # We take our list of rule variations from the forecasts, since it
        # might be that some rules were omitted in the weight calculation
        forecast_weights = self.get_forecast_weights(instrument_code)
        rule_variation_list = list(forecast_weights.columns)

        forecasts = self.get_all_forecasts(
            instrument_code, rule_variation_list)

        weighted_forecasts = forecast_weights.ffill() * forecasts

        return weighted_forecasts

    # GET FORECAST WEIGHTS ALIGNED TO FORECASTS AND SMOOTHED
    @diagnostic()
    def get_forecast_weights(self, instrument_code: str):
        """
        Get the forecast weights

        We forward fill all forecasts. We then adjust forecast weights so that
          they are 1.0 in every period; after setting to zero when no forecast
          is available.

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
        self.log.msg(
            "Calculating forecast weights for %s" % (instrument_code),
            instrument_code=instrument_code,
        )

        # note these might include missing weights, eg too expensive, or absent
        # from fixed weights
        # These are monthly to save space
        monthly_forecast_weights = self.get_raw_monthly_forecast_weights(instrument_code)

        # smooth out weights
        forecast_smoothing_ewma_span= self.parent.config.forecast_weight_ewma_span
        smoothed_monthly_forecast_weights = monthly_forecast_weights.ewm(span=forecast_smoothing_ewma_span).mean()

        # fix to forecast time series
        forecast_weights_fixed_to_forecasts = self._fix_weights_to_forecasts(
            instrument_code=instrument_code,
            smoothed_monthly_forecast_weights=smoothed_monthly_forecast_weights
            )


        return forecast_weights_fixed_to_forecasts

    @dont_cache
    def _fix_weights_to_forecasts(self,instrument_code: str,
                                  smoothed_monthly_forecast_weights: pd.DataFrame) -> pd.DataFrame:
        # we get the rule variations from forecast_weight columns, as if we've dropped
        # expensive rules (when estimating) then get_trading_rules will give
        # the wrong answer
        rule_variation_list = list(smoothed_monthly_forecast_weights.columns)
        forecasts = self.get_all_forecasts(
            instrument_code, rule_variation_list)

        # adjust weights for missing data
        # also aligns them together with forecasts
        forecast_weights_fixed_to_forecasts = \
            fix_weights_vs_position_or_forecast(smoothed_monthly_forecast_weights,
                                                forecasts)

        return forecast_weights_fixed_to_forecasts

    # GET FORECASTS
    @input
    def get_all_forecasts(self,
                          instrument_code: str,
                          rule_variation_list: list=None) -> pd.DataFrame:
        """
        Returns a data frame of forecasts for a particular instrument

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

        if rule_variation_list is None:
            rule_variation_list = self.get_trading_rule_list(instrument_code)

        forecasts = self.get_forecasts_given_rule_list(
            instrument_code, rule_variation_list
        )

        return forecasts

    @dont_cache
    def get_trading_rule_list(self, instrument_code: str)-> list:
        """
        Get list of trading rules

        We remove any rules with a constant zero or nan forecast

        :param instrument_code:
        :return: list of str
        """

        if self._use_estimated_weights():
            # Note for estimated weights we apply the 'is this cheap enough'
            # rule, but not here
            trial_rule_list = self.get_trading_rule_list_for_estimated_weights(
                instrument_code
            )
        else:
            trial_rule_list = self._get_trading_rule_list_with_fixed_weights(
                instrument_code)

        return trial_rule_list

    @diagnostic()
    def _get_trading_rule_list_with_fixed_weights(self, instrument_code: str) -> list:
        """
        Get list of all trading rule names when weights are fixed

        If we have fixed weights use those; otherwise get from trading rules


        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping
        >>> from systems.basesystem import System
        >>> (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping()
        >>> system=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>>
        >>> system.combForecast.get_trading_rule_list("EDOLLAR")
        ['ewmac16', 'ewmac8']
        """

        # Let's try the config
        system = self.parent
        if hasattr(system.config, "forecast_weights"):
            # a dict of weights, nested or un nested
            if instrument_code in system.config.forecast_weights:
                # nested dict
                rules = system.config.forecast_weights[instrument_code].keys()
            else:
                # assume it's a non nested dict, eg weights same across instruments
                rules = system.config.forecast_weights.keys()
        else:
            ## not supplied as a config item, use the name of the rules
            rules = self._get_list_of_all_trading_rules_from_forecasting_stage()

        rules = sorted(rules)

        return rules

    @input
    def _get_list_of_all_trading_rules_from_forecasting_stage(self) -> list:
        return list(self.parent.rules.trading_rules().keys())

    @diagnostic()
    def get_trading_rule_list_for_estimated_weights(self, instrument_code: str) -> list:
        """
        Get list of all trading rule names when weights are estimated

        If rule_variations is specified in config use that, otherwise use all available rules

        :param instrument_code:
        :type str:

        :returns: list of str

        KEY INPUT

        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping_estimate
        >>> from systems.basesystem import System
        >>> (accounts, fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping_estimate()
        >>> system=System([accounts, rawdata, rules, fcs, ForecastCombineEstimated()], data, config)
        >>> system.combForecast.get_trading_rule_list("EDOLLAR")
        ['carry', 'ewmac16', 'ewmac8']
        >>> system.config.rule_variations=dict(EDOLLAR=["ewmac8"])
        >>> system.combForecast.get_trading_rule_list("EDOLLAR")
        ['ewmac8']
        """
        # Let's try the config
        system = self.parent

        if hasattr(system.config, "rule_variations"):
            ###
            if instrument_code in system.config.rule_variations:
                # nested dict of lists
                rules = system.config.rule_variations[instrument_code]
            else:
                # assume it's a non nested list
                # this will break if you have put an incomplete list of
                # instruments into a nested dict
                rules = system.config.rule_variations
        else:
            ## not supplied in config
            rules = self.parent.rules.trading_rules().keys()

        rules = sorted(rules)

        return rules


    @diagnostic()
    def get_forecasts_given_rule_list(
            self, instrument_code: str,
            rule_variation_list: list) -> pd.Series:
        """
        Convenience function to get a list of forecasts

        :param instrument_code: str
        :param rule_variation_list: list of str
        :return: pd.DataFrame
        """
        forecasts = [
            self._get_capped_individual_forecast(instrument_code, rule_variation_name)
            for rule_variation_name in rule_variation_list
        ]

        forecasts = pd.concat(forecasts, axis=1)

        forecasts.columns = rule_variation_list

        forecasts = forecasts.ffill()

        return forecasts


    @input
    def _get_capped_individual_forecast(self, instrument_code: str,
                                        rule_variation_name: str)-> pd.Series:
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
        >>> system.combForecast._get_capped_individual_forecast("EDOLLAR","ewmac8").tail(2)
                      ewmac8
        2015-12-10 -0.190583
        2015-12-11  0.871231
        """

        return self.parent.forecastScaleCap.get_capped_forecast(
            instrument_code, rule_variation_name
        )


    # FORECAST WEIGHT CALCULATIONS
    @dont_cache
    def get_raw_monthly_forecast_weights(self, instrument_code: str) -> pd.DataFrame:
        """
        Get forecast weights depending on whether we are estimating these or
        not

        :param instrument_code: str
        :return: forecast weights
        """

        # get raw weights
        if self._use_estimated_weights():
            forecast_weights = self.get_monthly_raw_forecast_weights_estimated(
                instrument_code)
        else:
            ## these won't be monthly, but will be length 2
            forecast_weights = self.get_raw_fixed_forecast_weights(
                instrument_code)

        return forecast_weights


    @dont_cache
    def _use_estimated_weights(self):
        return str2Bool(self.parent.config.use_forecast_weight_estimates)

    def get_monthly_raw_forecast_weights_estimated(self, instrument_code: str) -> pd.DataFrame:
        """
        Estimate the forecast weights for this instrument

        :param instrument_code:
        :type str:

        :returns: TxK pd.DataFrame containing weights, columns are trading rule variation names, T covers all

        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping_estimate
        >>> from systems.basesystem import System
        >>> (accounts, fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping_estimate()
        >>> system=System([accounts, rawdata, rules, fcs, ForecastCombineEstimated()], data, config)
        >>> system.config.forecast_weight_estimate['method']="shrinkage"
        >>> system.combForecast.get_raw_monthly_forecast_weights("EDOLLAR").tail(3)
                       carry   ewmac16    ewmac8
        2015-05-30  0.437915  0.258300  0.303785
        2015-06-01  0.442438  0.256319  0.301243
        2015-12-12  0.442438  0.256319  0.301243
        >>> system.delete_all_items(True)
        >>> system.config.forecast_weight_estimate['method']="one_period"
        >>> system.combForecast.get_raw_monthly_forecast_weights("EDOLLAR").tail(3)
        2015-05-30  0.484279  8.867313e-17  0.515721
        2015-06-01  0.515626  7.408912e-17  0.484374
        2015-12-12  0.515626  7.408912e-17  0.484374
        >>> system.delete_all_items(True)
        >>> system.config.forecast_weight_estimate['method']="bootstrap"
        >>> system.config.forecast_weight_estimate['monte_runs']=50
        >>> system.combForecast.get_raw_monthly_forecast_weights("EDOLLAR").tail(3)
                       carry   ewmac16    ewmac8
        2015-05-30  0.446446  0.222678  0.330876
        2015-06-01  0.464240  0.192962  0.342798
        2015-12-12  0.464240  0.192962  0.342798
        """
        #FIXME REFACTOR
        return self.calculation_of_raw_estimated_monthly_forecast_weights(
            instrument_code
        ).weights

    @diagnostic()
    def calculation_of_raw_estimated_monthly_forecast_weights(self, instrument_code):
        """
        Does an optimisation for a single instrument

        We do this if we can't do the special case of a fully pooled
        optimisation (both costs and returns pooled)

        Estimate the forecast weights for this instrument

        We store this intermediate step to expose the calculation object

        :param instrument_code:
        :type str:

        :returns: TxK pd.DataFrame containing weights, columns are trading rule variation names, T covers all
        """
        #FIXME REFACTOR

        self.log.terse(
            "Calculating raw forecast weights for %s" %
            instrument_code)

        # Get some useful stuff from the config
        weighting_params = copy(self.parent.config.forecast_weight_estimate)
        cost_param = copy(self.parent.config.forecast_cost_estimates)
        weighting_params.update(cost_param)

        # which function to use for calculation
        weighting_func = resolve_function(weighting_params.pop("func"))

        # Because we might be pooling, we get a stack of p&l data
        codes_to_use = self.has_same_cheap_rules_as_code(instrument_code)

        # returns a dict of accountCurveGroups
        # Note that the config.forecast_cost_estimates parameters will affect
        # the costs shown in these returns
        # They could all be equal, or
        pandl_forecasts = dict(
            [(code, self.get_returns_for_optimisation(code)) for code in codes_to_use]
        )

        weight_func = weighting_func(
            pandl_forecasts,
            identifier=instrument_code,
            parent=self,
            **weighting_params)

        weight_func.optimise()

        return weight_func

    @dont_cache
    def has_same_cheap_rules_as_code(self, instrument_code: str) -> list:
        """
        Returns all instruments with same set of trading rules as this one, after max cost applied

        :param instrument_code:
        :type str:

        :returns: list of str

        """

        my_rules = self.cheap_trading_rules(instrument_code)
        instrument_list = self.parent.get_instrument_list()

        def _rule_list_matches(list_of_rules, other_list_of_rules):
            list_of_rules.sort()
            other_list_of_rules.sort()
            return list_of_rules == other_list_of_rules

        matching_instruments = \
            [
                other_code
                for other_code in instrument_list
                if _rule_list_matches(my_rules, self.cheap_trading_rules(other_code))
            ]

        matching_instruments.sort()

        return matching_instruments

    @diagnostic()
    def cheap_trading_rules(self, instrument_code: str) -> list:
        """
        Returns a list of trading rules which are cheap enough to trade, given a max tolerable
          annualised SR cost

        :param instrument_code:
        :type str:

        :returns: list of str


        """

        ceiling_cost_SR = self.parent.config.forecast_weight_estimate["ceiling_cost_SR"]

        rule_list = self.get_trading_rule_list(instrument_code)
        SR_cost_list = [
            self.get_SR_cost_for_instrument_forecast(
                instrument_code, rule_variation_name
            )
            for rule_variation_name in rule_list
        ]

        cheap_rule_list = [
            rule_name
            for (rule_name, rule_cost) in zip(rule_list, SR_cost_list)
            if rule_cost <= ceiling_cost_SR
        ]

        if len(cheap_rule_list) == 0:
            self.log.critical(
                "No rules are cheap enough for %s with threshold %.3f SR units! Raise threshold (system.config.forecast_weight_estimate['ceiling_cost_SR']), add rules, or drop instrument." %
                (instrument_code, ceiling_cost_SR))
        else:
            self.log.msg(
                "Only this set of rules %s is cheap enough to trade for %s"
                % (str(cheap_rule_list), instrument_code),
                instrument_code=instrument_code,
            )

        return cheap_rule_list

    @input
    def get_SR_cost_for_instrument_forecast(
            self, instrument_code: str,
            rule_variation_name: str):
        """

        Get the cost in SR units per year of trading this instrument / rule

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str:

        :returns: float

        KEY INPUT
        """
        if not hasattr(self.parent, "accounts"):
            warn_msg = (
                "You need an accounts stage in the system to estimate forecast costs for %s %s. Using costs of zero" % (instrument_code, rule_variation_name)
            )
            self.log.warn(warn_msg)

            return 0.0

        return self.parent.accounts.get_SR_cost_for_instrument_forecast(
            instrument_code, rule_variation_name
        )

    @input
    def get_returns_for_optimisation(self, instrument_code: str) -> pd.DataFrame:
        """
        Get pandl for instrument rules
        THese will include both gross and net returns, in case we do any pooling

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: accountCurveGroup object

        """
        if not hasattr(self.parent, "accounts"):
            error_msg = (
                "You need an accounts stage in the system to estimate forecast weights"
            )
            self.log.critical(error_msg)

        cheap_rule_list = self.cheap_trading_rules(instrument_code)
        return self.parent.accounts.pandl_for_instrument_rules_unweighted(
            instrument_code, cheap_rule_list
        )


    # FIXED FORECAST WEIGHTS

    def get_raw_fixed_forecast_weights(self, instrument_code: str) -> pd.DataFrame:
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
        >>> system.combForecast.get_raw_monthly_forecast_weights("EDOLLAR").tail(2)
                    ewmac16  ewmac8
        2015-12-10      0.5     0.5
        2015-12-11      0.5     0.5
        >>>
        >>> config.forecast_weights=dict(EDOLLAR=dict(ewmac8=0.9, ewmac16=0.1))
        >>> system2=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system2.combForecast.get_raw_monthly_forecast_weights("EDOLLAR").tail(2)
                    ewmac16  ewmac8
        2015-12-10      0.1     0.9
        2015-12-11      0.1     0.9
        >>>
        >>> del(config.forecast_weights)
        >>> system3=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system3.combForecast.get_raw_monthly_forecast_weights("EDOLLAR").tail(2)
        WARNING: No forecast weights  - using equal weights of 0.5000 over all 2 trading rules in system
                    ewmac16  ewmac8
        2015-12-10      0.5     0.5
        2015-12-11      0.5     0.5
        """


        # Now we have a dict, fixed_weights.
        # Need to turn into a timeseries covering the range of forecast
        # dates

        fixed_weights = self._get_fixed_forecast_weights_as_dict(instrument_code)

        rule_variation_list = sorted(fixed_weights.keys())

        forecasts_ts = self.get_all_forecasts(
            instrument_code, rule_variation_list)

        forecast_weights = from_dict_of_values_to_df(
            fixed_weights, forecasts_ts.index, columns=forecasts_ts.columns
        )

        return forecast_weights

    @diagnostic()
    def _get_fixed_forecast_weights_as_dict(self, instrument_code: str) -> dict:
        config = self.parent.config
        # Let's try the config
        forecast_weights_config = config.get_element_or_missing_data("forecast_weights")

        if forecast_weights_config is missing_data:
            fixed_weights = self._get_one_over_n_weights(instrument_code)
        else:
            fixed_weights = _get_fixed_weights_from_config(forecast_weights_config=forecast_weights_config,
                                                           instrument_code=instrument_code,
                                                           log=self.log)
        return fixed_weights

    def _get_one_over_n_weights(self,instrument_code: str) -> dict:
        rules = self.get_trading_rule_list(instrument_code)
        equal_weight = 1.0 / len(rules)

        warn_msg = (
                "WARNING: No forecast weights  - using equal weights of %.3f over all %d trading rules in system" %
                (equal_weight, len(rules)))

        self.log.warn(warn_msg, instrument_code=instrument_code)

        fixed_weights = dict([(rule_name, equal_weight)
                              for rule_name in rules])

        return fixed_weights



    # DIVERSIFICATION MULTIPLIER
    @dont_cache
    def get_monthly_forecast_diversification_multiplier(self, instrument_code):
        if self.use_estimated_div_mult():
            fdm = self.get_monthly_forecast_diversification_multiplier_estimated(
                instrument_code
            )
        else:
            fdm = self.get_forecast_diversification_multiplier_fixed(
                instrument_code)

        return fdm

    @dont_cache
    def use_estimated_div_mult(self):
        return str2Bool(self.parent.config.use_forecast_div_mult_estimates)


    # FIXED FDM
    @diagnostic()
    def get_forecast_diversification_multiplier_fixed(self, instrument_code: str) -> pd.Series:
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
        >>> system.combForecast.get_monthly_forecast_diversification_multiplier("EDOLLAR").tail(2)
                    fdm
        2015-12-10  1.1
        2015-12-11  1.1
        >>>
        >>> config.forecast_div_multiplier=dict(EDOLLAR=2.0)
        >>> system2=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system2.combForecast.get_monthly_forecast_diversification_multiplier("EDOLLAR").tail(2)
                    fdm
        2015-12-10    2
        2015-12-11    2
        >>>
        >>> ## defaults
        >>> del(config.forecast_div_multiplier)
        >>> system3=System([rawdata, rules, fcs, ForecastCombineFixed()], data, config)
        >>> system3.combForecast.get_monthly_forecast_diversification_multiplier("EDOLLAR").tail(2)
                    fdm
        2015-12-10    1
        2015-12-11    1
        """

        # Let's try the config
        system = self.parent
        forecast_div_multiplier_config = \
            system.config.get_element_or_missing_data("forecast_div_multiplier")

        fixed_div_mult = _get_fixed_fdm_scalar_value_from_config(forecast_div_multiplier_config=forecast_div_multiplier_config,
                                                                 instrument_code=instrument_code,
                                                                 log=self.log)
        # Now we have a dict, fixed_weights.
        # Need to turn into a timeseries covering the range of forecast dates
        # get forecast weights first
        forecast_weights = self.get_forecast_weights(instrument_code)

        fixed_div_mult_as_ts = from_scalar_values_to_ts(fixed_div_mult, forecast_weights.index)

        return fixed_div_mult_as_ts

    # ESTIMATED FDM


    @diagnostic(protected=True)
    # FIXME REFACTOR
    def get_monthly_forecast_diversification_multiplier_estimated(
            self, instrument_code: str) -> pd.Series:
        """

        Get the diversification multiplier for this instrument

        Estimated from correlations and weights

        :param instrument_code: instrument to get multiplier for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame



        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping_estimate
        >>> from systems.basesystem import System
        >>> (accounts, fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping_estimate()
        >>> system=System([accounts, rawdata, rules, fcs, ForecastCombineEstimated()], data, config)
        >>> system.config.forecast_weight_estimate['method']="shrinkage"
        >>> system.combForecast.get_monthly_forecast_diversification_multiplier("EDOLLAR").tail(3)
                         FDM
        2015-12-09  1.367351
        2015-12-10  1.367349
        2015-12-11  1.367347
        >>> system.config.forecast_div_mult_estimate['dm_max']=1.1
        >>> system=System([accounts, rawdata, rules, fcs, ForecastCombineEstimated()], data, system.config)
        >>> system.combForecast.get_monthly_forecast_diversification_multiplier("EDOLLAR").tail(3)
                    FDM
        2015-12-09  1.1
        2015-12-10  1.1
        2015-12-11  1.1
        """
        self.log.terse(
            "Calculating forecast div multiplier for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        # Get some useful stuff from the config
        div_mult_params = copy(self.parent.config.forecast_div_mult_estimate)

        # an example of an idm calculation function is
        # syscore.divmultipliers.diversification_multiplier_from_list
        idm_func = resolve_function(div_mult_params.pop("func"))

        correlation_list_object = self.get_forecast_correlation_matrices(
            instrument_code
        )

        weight_df = self.get_forecast_weights(instrument_code)

        # note there is a possibility that the forecast_weights contain a subset of the rules in the correlation
        #    matrices, because the forecast weights could have rules removed for being too expensive
        # To deal with this we pad the weights data frame so it is exactly
        # aligned with the correlations

        weight_df = dataframe_pad(
            weight_df, correlation_list_object.columns, padwith=0.0
        )

        ts_fdm = idm_func(
            correlation_list_object,
            weight_df,
            **div_mult_params)

        return ts_fdm





    @diagnostic(protected=True, not_pickable=True)
    def get_forecast_correlation_matrices_from_code_list(self, codes_to_use):
        """
        Returns a correlationList object which contains a history of correlation matricies

        :param codes_to_use:
        :type str:

        :returns: correlation_list object

        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping_estimate
        >>> from systems.basesystem import System
        >>> (accounts, fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping_estimate()
        >>> system=System([rawdata, rules, fcs, accounts, ForecastCombineEstimated()], data, config)
        >>> ans=system.combForecast.get_forecast_correlation_matrices("EDOLLAR")
        >>> ans.corr_list[-1]
        array([[ 1.        ,  0.1168699 ,  0.08038547],
               [ 0.1168699 ,  1.        ,  0.86907623],
               [ 0.08038547,  0.86907623,  1.        ]])
        >>> print(ans.columns)
        ['carry', 'ewmac16', 'ewmac8']
        """

        # Get some useful stuff from the config
        corr_params = copy(self.parent.config.forecast_correlation_estimate)

        # do we pool our estimation?
        pooling = str2Bool(corr_params.pop("pool_instruments"))

        # which function to use for calculation
        corr_func = resolve_function(corr_params.pop("func"))

        self.log.terse(
            "Calculating forecast correlations over %s" %
            ", ".join(codes_to_use))

        forecast_data = [
            self.get_all_forecasts(instr_code, self.get_trading_rule_list(instr_code))
            for instr_code in codes_to_use
        ]

        # if we're not pooling passes a list of one
        forecast_data = [forecast_ts.ffill() for forecast_ts in forecast_data]

        return corr_func(forecast_data, **corr_params)

    @diagnostic(protected=True, not_pickable=True)
    def get_forecast_correlation_matrices(self, instrument_code):
        """
        Returns a correlationList object which contains a history of correlation matricies

        :param instrument_code:
        :type str:

        :returns: correlation_list object

        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping_estimate
        >>> from systems.basesystem import System
        >>> (accounts, fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping_estimate()
        >>> system=System([rawdata, rules, fcs, accounts, ForecastCombineEstimated()], data, config)
        >>> ans=system.combForecast.get_forecast_correlation_matrices("EDOLLAR")
        >>> ans.corr_list[-1]
        array([[ 1.        ,  0.1168699 ,  0.08038547],
               [ 0.1168699 ,  1.        ,  0.86907623],
               [ 0.08038547,  0.86907623,  1.        ]])
        >>> print(ans.columns)
        ['carry', 'ewmac16', 'ewmac8']
        """

        # Get some useful stuff from the config
        corr_params = copy(self.parent.config.forecast_correlation_estimate)

        # do we pool our estimation?
        pooling = str2Bool(corr_params.pop("pool_instruments"))

        if pooling:
            # find set of instruments with same trading rules as I have
            if self._use_estimated_weights():
                codes_to_use = self.has_same_cheap_rules_as_code(
                    instrument_code)
            else:
                codes_to_use = self.has_same_rules_as_code(instrument_code)
        else:
            codes_to_use = [instrument_code]

        forecast_corr_list = self.get_forecast_correlation_matrices_from_code_list(
            codes_to_use)

        return forecast_corr_list



    @diagnostic()
    def has_same_rules_as_code(self, instrument_code: str) -> list:
        """
        Returns all instruments with same set of trading rules as this one

        :param instrument_code:
        :type str:

        :returns: list of str


        >>> from systems.tests.testdata import get_test_object_futures_with_rules_and_capping_estimate
        >>> from systems.basesystem import System
        >>> (accounts, fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping_estimate()
        >>> system=System([accounts, rawdata, rules, fcs, ForecastCombineEstimated()], data, config)
        >>> system.combForecast.has_same_rules_as_code("EDOLLAR")
        ['EDOLLAR', 'US10']
        >>> system.combForecast.has_same_rules_as_code("BUND")
        ['BUND']
        """

        my_rules = self.get_trading_rule_list(instrument_code)
        instrument_list = self.parent.get_instrument_list()

        def _matches(xlist, ylist):
            xlist.sort()
            ylist.sort()
            return xlist == ylist

        matching_instruments = sorted(
            [
                other_code
                for other_code in instrument_list
                if _matches(my_rules, self.get_trading_rule_list(other_code))
            ]
        )

        return matching_instruments



    # FORECAST MAPPING
    @diagnostic(not_pickable=True)
    # FIXME REFACTOR
    def _get_forecast_mapping_function(self, instrument_code):
        """
        Get the function to apply non linear forecast mapping, and any parameters

        :param instrument_code: instrument code
        :return: (function, kwargs) to do the mapping, with arguments
        """

        forecast_cap = self.get_forecast_cap()
        forecast_floor = self.get_forecast_floor()
        if hasattr(self.parent.config, "forecast_mapping"):
            if instrument_code in self.parent.config.forecast_mapping:
                configuration = self.parent.config.forecast_mapping[instrument_code]
                post_process_func = map_forecast_value
                kwargs = dict(
                    threshold=configuration["threshold"],
                    a_param=configuration["a_param"],
                    b_param=configuration["b_param"],
                    capped_value=forecast_cap,
                )
                self.log.msg(
                    "Applying threshold mapping for %s threshold %.2f"
                    % (instrument_code, configuration["threshold"]),
                    instrument_code=instrument_code,
                )
                return post_process_func, kwargs

        # just use the default, applying capping
        post_process_func = _cap_combined_forecast
        kwargs = dict(forecast_cap=forecast_cap,
                      forecast_floor = forecast_floor)
        self.log.msg(
            "No mapping applied for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        return post_process_func, kwargs


    @input
    def get_forecast_cap(self) -> float:
        """
        Get the forecast cap from the previous module

        :returns: float

        KEY INPUT
        """

        return self.parent.forecastScaleCap.get_forecast_cap()

    @input
    def get_forecast_floor(self) -> float:
        """
        Get the forecast cap from the previous module

        :returns: float

        KEY INPUT
        """

        return self.parent.forecastScaleCap.get_forecast_floor()



def _cap_combined_forecast(
        raw_multiplied_combined_forecast: pd.Series,
        forecast_cap: float=20.0,
        forecast_floor: float=-20) -> pd.Series:

    capped_combined_forecast = raw_multiplied_combined_forecast.clip(
        lower=forecast_floor, upper=forecast_cap
    )
    return capped_combined_forecast

def _get_fixed_weights_from_config(forecast_weights_config: dict,
                                   instrument_code: str,
                                   log) -> dict:
    if instrument_code in forecast_weights_config:
        # nested dict
        fixed_weights = forecast_weights_config[instrument_code]
        log.msg("Nested dict of forecast weights for %s %s: weights different by instrument" % (
                instrument_code, str(fixed_weights)))
    else:
        # assume it's a non nested dict
        fixed_weights = forecast_weights_config
        log.msg("Non-nested dict of forecast weights for %s %s: weights the same for all instruments" % (
                instrument_code, str(fixed_weights)))

    return fixed_weights

def _get_fixed_fdm_scalar_value_from_config(forecast_div_multiplier_config: dict,
                                            instrument_code: str,
                                            log) -> float:

    error_msg = ""
    fixed_div_mult = None

    if forecast_div_multiplier_config is missing_data:
        error_msg = "Need to specify 'forecast_div_multiplier' in config or system_defaults"

    if isinstance(forecast_div_multiplier_config, float) or isinstance(forecast_div_multiplier_config, int):
        fixed_div_mult = forecast_div_multiplier_config

    elif isinstance(forecast_div_multiplier_config, dict):
        fixed_div_mult = forecast_div_multiplier_config.get(instrument_code, None)
        if fixed_div_mult is None:
            error_msg = "Instrument %s missing from 'config.forecast_div_multiplier' dict" % instrument_code

    else:
        error_msg = "FDM in config needs to be either float, or dict with instrument_code keys"

    if error_msg=="":
        log.msg(
            "Using fixed FDM multiplier of %.3f for %s" %
            (fixed_div_mult, instrument_code), instrument_code=instrument_code)
    else:
        log.critical(error_msg, instrument_code=instrument_code)
        raise (error_msg)

    return fixed_div_mult


if __name__ == "__main__":
    import doctest

    doctest.testmod()

