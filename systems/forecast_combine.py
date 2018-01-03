from copy import copy

import numpy as np
import pandas as pd

from syscore.genutils import str2Bool
from syscore.objects import resolve_function, update_recalc
from syscore.pdutils import (apply_cap, dataframe_pad, fix_weights_vs_pdm,
                             from_dict_of_values_to_df)
from systems.defaults import system_defaults
from systems.stage import SystemStage
from systems.system_cache import diagnostic, dont_cache, input, output


class _ForecastCombinePreCalculate(SystemStage):
    """
    Don't use - forms part of ForecastCombine
    """


    def _name(self):
        return "*DO NOT USE*"

    @dont_cache
    def _use_estimated_weights(self):
        return str2Bool(self.parent.config.use_forecast_weight_estimates)

    @input
    def get_forecast_cap(self):
        """
        Get the forecast cap from the previous module

        :returns: float

        KEY INPUT
        """

        return self.parent.forecastScaleCap.get_forecast_cap()

    @input
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


    @diagnostic()
    def get_trading_rule_list_estimated_weights(self, instrument_code):
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
                rules = system.config.rule_variations[
                    instrument_code]
            else:
                # assume it's a non nested list
                # this will break if you have put an incomplete list of instruments into a nested dict
                rules = system.config.rule_variations
        else:
            ## not supplied in config
            rules = self.parent.rules.trading_rules().keys()

        rules = sorted(rules)

        return rules

    @diagnostic()
    def _get_trading_rule_list_fixed_weights(self, instrument_code):
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
                rules = system.config.forecast_weights[
                    instrument_code].keys()
            else:
                # assume it's a non nested dict
                rules = system.config.forecast_weights.keys()
        else:
            ## not supplied in config
            rules = self.parent.rules.trading_rules().keys()

        rules = sorted(rules)

        return rules

    @dont_cache
    def get_trading_rule_list(self, instrument_code):
        """
        Get list of trading rules


        :param instrument_code:
        :return: list of str
        """

        if self._use_estimated_weights():
            # Note for estimated weights we apply the 'is this cheap enough' rule, but not here
            return self.get_trading_rule_list_estimated_weights(instrument_code)
        else:
            return self._get_trading_rule_list_fixed_weights(instrument_code)

    @diagnostic()
    def has_same_rules_as_code(self, instrument_code):
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

        matching_instruments = sorted([other_code for other_code in instrument_list
                                       if _matches(my_rules, self.get_trading_rule_list(other_code))])

        return matching_instruments

    @input
    def get_all_forecasts(self, instrument_code, rule_variation_list=None):
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
            rule_variation_list = self.get_trading_rule_list(
                instrument_code)

        forecasts = [
            self.get_capped_forecast(
                instrument_code,
                rule_variation_name) for rule_variation_name in rule_variation_list]

        forecasts = pd.concat(forecasts, axis=1)

        forecasts.columns = rule_variation_list

        forecasts = forecasts.ffill()

        return forecasts


class _ForecastCombineCalculateWeights(_ForecastCombinePreCalculate):
    """
    Don't use - forms part of ForecastCombine
    """

    def _name(self):
        return "*DO NOT USE*"

    def get_raw_fixed_forecast_weights(self, instrument_code):
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

        system = self.parent
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
            rules = self.get_trading_rule_list(instrument_code)
            equal_weight = 1.0 / len(rules)

            warn_msg = "WARNING: No forecast weights  - using equal weights of %.4f over all %d trading rules in system" % (
                equal_weight, len(rules))

            self.log.warn(warn_msg, instrument_code=instrument_code)

            fixed_weights = dict([(rule_name, equal_weight)
                                  for rule_name in rules])

        # Now we have a dict, fixed_weights.
        # Need to turn into a timeseries covering the range of forecast
        # dates
        rule_variation_list = sorted(fixed_weights.keys())

        forecasts_ts = self.get_all_forecasts(
            instrument_code, rule_variation_list)

        forecast_weights = from_dict_of_values_to_df(fixed_weights, forecasts_ts.index, columns = forecasts_ts.columns)

        return forecast_weights

    @input
    def get_SR_cost_for_instrument_forecast(
            self, instrument_code, rule_variation_name):
        """

        Get the cost in SR units per year of trading this instrument / rule

        :param instrument_code:
        :type str:

        :param rule_variation_name:
        :type str:

        :returns: float

        KEY INPUT
        """

        return self.parent.accounts.get_SR_cost_for_instrument_forecast(
            instrument_code, rule_variation_name)

    @diagnostic()
    def cheap_trading_rules(self, instrument_code):
        """
        Returns a list of trading rules which are cheap enough to trade, given a max tolerable
          annualised SR cost

        :param instrument_code:
        :type str:

        :returns: list of str


        """

        ceiling_cost_SR = self.parent.config.forecast_weight_estimate[
            'ceiling_cost_SR']

        rule_list = self.get_trading_rule_list(instrument_code)
        SR_cost_list = [self.get_SR_cost_for_instrument_forecast(instrument_code, rule_variation_name)
                        for rule_variation_name in rule_list]

        cheap_rule_list = [rule_name for (rule_name, rule_cost) in zip(rule_list, SR_cost_list)
                           if rule_cost <= ceiling_cost_SR]

        if len(cheap_rule_list) == 0:
            self.log.critical(
                "No rules are cheap enough for %s with threshold %.3f SR units! Raise threshold (system.config.forecast_weight_estimate['ceiling_cost_SR']), add rules, or drop instrument." %
                (instrument_code, ceiling_cost_SR))

        self.log.msg("Only this set of rules %s is cheap enough to trade for %s" % (str(cheap_rule_list), instrument_code),
                           instrument_code=instrument_code)

        return cheap_rule_list



    @input
    def get_returns_for_optimisation(self, instrument_code):
        """
        Get pandl for instrument rules
        THese will include both gross and net returns, in case we do any pooling

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: accountCurveGroup object

        """
        if not hasattr(self.parent, "accounts"):
            error_msg = "You need an accounts stage in the system to estimate forecast weights"
            self.log.critical(error_msg)

        cheap_rule_list = self.cheap_trading_rules(instrument_code)
        return self.parent.accounts.pandl_for_instrument_rules_unweighted(
            instrument_code, cheap_rule_list)


    @dont_cache
    def has_same_cheap_rules_as_code(self, instrument_code):
        """
        Returns all instruments with same set of trading rules as this one, after max cost applied

        :param instrument_code:
        :type str:

        :returns: list of str

        """

        my_rules = self.cheap_trading_rules(instrument_code)
        instrument_list = self.parent.get_instrument_list()

        def _matches(xlist, ylist):
            xlist.sort()
            ylist.sort()
            return xlist == ylist

        matching_instruments = sorted([other_code for other_code in instrument_list
                                       if _matches(my_rules, self.cheap_trading_rules(other_code))])

        return matching_instruments


    @diagnostic()
    def calculation_of_raw_estimated_forecast_weights(self, instrument_code):
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
        pandl_forecasts = dict([(code, self.get_returns_for_optimisation(code))
                           for code in codes_to_use])

        weight_func = weighting_func(pandl_forecasts,
                                     identifier=instrument_code,
                                     parent=self, **weighting_params)

        weight_func.optimise()
        return weight_func

    def get_raw_forecast_weights_estimated(self, instrument_code):
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
        >>> system.combForecast.get_raw_forecast_weights("EDOLLAR").tail(3)
                       carry   ewmac16    ewmac8
        2015-05-30  0.437915  0.258300  0.303785
        2015-06-01  0.442438  0.256319  0.301243
        2015-12-12  0.442438  0.256319  0.301243
        >>> system.delete_all_items(True)
        >>> system.config.forecast_weight_estimate['method']="one_period"
        >>> system.combForecast.get_raw_forecast_weights("EDOLLAR").tail(3)
        2015-05-30  0.484279  8.867313e-17  0.515721
        2015-06-01  0.515626  7.408912e-17  0.484374
        2015-12-12  0.515626  7.408912e-17  0.484374
        >>> system.delete_all_items(True)
        >>> system.config.forecast_weight_estimate['method']="bootstrap"
        >>> system.config.forecast_weight_estimate['monte_runs']=50
        >>> system.combForecast.get_raw_forecast_weights("EDOLLAR").tail(3)
                       carry   ewmac16    ewmac8
        2015-05-30  0.446446  0.222678  0.330876
        2015-06-01  0.464240  0.192962  0.342798
        2015-12-12  0.464240  0.192962  0.342798
        """
        return self.calculation_of_raw_estimated_forecast_weights(
                instrument_code).weights

    @dont_cache
    def get_raw_forecast_weights(self, instrument_code):
        """
        Get forecast weights depending on whether we are estimating these or
        not

        :param instrument_code: str
        :return: forecast weights
        """

        # get raw weights
        if self._use_estimated_weights():
            forecast_weights = self.get_raw_forecast_weights_estimated(instrument_code)
        else:
            forecast_weights = self.get_raw_fixed_forecast_weights(instrument_code)

        return forecast_weights

    @diagnostic()
    def get_forecast_weights(self, instrument_code):
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
        self.log.msg("Calculating forecast weights for %s" % (instrument_code),
        instrument_code=instrument_code)

        # note these might include missing weights, eg too expensive, or absent
        # from fixed weights
        forecast_weights = self.get_raw_forecast_weights(instrument_code)

        # we get the rule variations from forecast_weight columns, as if we've dropped
        #   expensive rules (when estimating) then get_trading_rules will give the wrong answer
        rule_variation_list = list(forecast_weights.columns)
        forecasts = self.get_all_forecasts(
            instrument_code, rule_variation_list)

        # adjust weights for missing data
        # also aligns them together with forecasts
        forecast_weights = fix_weights_vs_pdm(forecast_weights, forecasts)

        weighting = self.parent.config.forecast_weight_ewma_span

        # smooth
        forecast_weights = forecast_weights.ewm(weighting).mean()
        return forecast_weights


class _ForecastCombineCalculateDivMult(_ForecastCombinePreCalculate):
    """
    Don't use - forms part of ForecastCombine
    """



    def _name(self):
        return "*DO NOT USE*"

    @diagnostic()
    def get_forecast_diversification_multiplier_fixed(self, instrument_code):
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
        system = self.parent
        self.log.msg("Calculating diversification multiplier for %s" % (instrument_code),
                           instrument_code=instrument_code)

        # Let's try the config
        if hasattr(system.config, "forecast_div_multiplier"):
            if isinstance(system.config.forecast_div_multiplier, float):
                fixed_div_mult = system.config.forecast_div_multiplier

            elif instrument_code in system.config.forecast_div_multiplier.keys():
                # dict
                fixed_div_mult = system.config.forecast_div_multiplier[
                    instrument_code]
            else:
                error_msg = "FDM in config needs to be either float, or dict with instrument_code keys"
                self.log.critical(
                    error_msg, instrument_code=instrument_code)

        elif "forecast_div_multiplier" in system_defaults:
            # try defaults
            fixed_div_mult = system_defaults['forecast_div_multiplier']
        else:
            error_msg = "Need to specify FDM in config or system_defaults"
            self.log.critical(
                error_msg, instrument_code=instrument_code)

        # Now we have a dict, fixed_weights.
        # Need to turn into a timeseries covering the range of forecast dates
        # get forecast weights first
        forecast_weights = self.get_forecast_weights(instrument_code)
        weight_ts = forecast_weights.index

        ts_fdm = pd.Series([fixed_div_mult] *
                           len(weight_ts), index=weight_ts)

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
            self.get_all_forecasts(
                instr_code,
                self.get_trading_rule_list(instr_code)) for instr_code in codes_to_use]

        # if we're not pooling passes a list of one
        forecast_data = [forecast_ts.ffill()
                         for forecast_ts in forecast_data]

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
            codes_to_use = self.has_same_cheap_rules_as_code(instrument_code)
        else:
            codes_to_use = [instrument_code]

        forecast_corr_list = self.get_forecast_correlation_matrices_from_code_list(codes_to_use)

        return forecast_corr_list


    @diagnostic(protected=True)
    def get_forecast_diversification_multiplier_estimated(self, instrument_code):
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
        >>> system.combForecast.get_forecast_diversification_multiplier("EDOLLAR").tail(3)
                         FDM
        2015-12-09  1.367351
        2015-12-10  1.367349
        2015-12-11  1.367347
        >>> system.config.forecast_div_mult_estimate['dm_max']=1.1
        >>> system=System([accounts, rawdata, rules, fcs, ForecastCombineEstimated()], data, system.config)
        >>> system.combForecast.get_forecast_diversification_multiplier("EDOLLAR").tail(3)
                    FDM
        2015-12-09  1.1
        2015-12-10  1.1
        2015-12-11  1.1
        """
        self.log.terse("Calculating forecast div multiplier for %s" % instrument_code,
                             instrument_code=instrument_code)

        # Get some useful stuff from the config
        div_mult_params = copy(self.parent.config.forecast_div_mult_estimate)

        # an example of an idm calculation function is syscore.divmultipliers.diversification_multiplier_from_list
        idm_func = resolve_function(div_mult_params.pop("func"))

        correlation_list_object = self.get_forecast_correlation_matrices(
            instrument_code)

        weight_df = self.get_forecast_weights(instrument_code)

        # note there is a possibility that the forecast_weights contain a subset of the rules in the correlation
        #    matrices, because the forecast weights could have rules removed for being too expensive
        # To deal with this we pad the weights data frame so it is exactly aligned with the correlations

        weight_df = dataframe_pad(weight_df, correlation_list_object.columns, padwith=0.0)

        ts_fdm = idm_func(
            correlation_list_object,
            weight_df,
            **div_mult_params)

        return ts_fdm

    @dont_cache
    def use_estimated_div_mult(self):
        return str2Bool(self.parent.config.use_forecast_div_mult_estimates)

    @dont_cache
    def get_forecast_diversification_multiplier(self, instrument_code):
        if self.use_estimated_div_mult():
            return self.get_forecast_diversification_multiplier_estimated(instrument_code)
        else:
            return self.get_forecast_diversification_multiplier_fixed(instrument_code)


class ForecastCombine(_ForecastCombineCalculateWeights,
                      _ForecastCombineCalculateDivMult):
    """
    Stage for combining forecasts (already capped and scaled)
    """

    def _name(self):
        return "combForecast"

    @output()
    def get_combined_forecast(self, instrument_code):
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
        self.log.msg("Calculating combined forecast for %s" % (instrument_code),
                           instrument_code=instrument_code)
        raw_multiplied_combined_forecast = self._get_raw_combined_forecast(instrument_code)

        # apply cap
        combined_forecast = self._cap_forecast(raw_multiplied_combined_forecast)
        return combined_forecast

    def _get_raw_combined_forecast(self, instrument_code):
        # We take our list of rule variations from the forecasts, since it
        # might be that some rules were omitted in the weight calculation
        forecast_weights = self.get_forecast_weights(instrument_code)
        rule_variation_list = list(forecast_weights.columns)

        forecasts = self.get_all_forecasts(
            instrument_code, rule_variation_list)
        forecast_div_multiplier = self.get_forecast_diversification_multiplier(
            instrument_code)

        weighted_forecasts = forecast_weights.ffill() * forecasts

        # sum
        raw_combined_forecast = weighted_forecasts.sum(axis=1)

        # apply fdm
        raw_multiplied_combined_forecast = (raw_combined_forecast *
                                            forecast_div_multiplier.ffill())
        return raw_multiplied_combined_forecast


    def _cap_forecast(self, raw_multiplied_combined_forecast):
        forecast_cap = self.get_forecast_cap()
        combined_forecast = apply_cap(raw_multiplied_combined_forecast,
                                      forecast_cap)
        return combined_forecast


class ForecastCombineMaybeThreshold(ForecastCombine):

    def get_combined_forecast(self, instrument_code):

        if instrument_code in self.parent.config.instruments_with_threshold:
            post_process_func = self._threshold_forecast
        else:
            post_process_func = self._cap_forecast

        self.log.msg("Calculating combined forecast for %s with %s" % (instrument_code, post_process_func.__name__),
                           instrument_code=instrument_code)

        raw_multiplied_combined_forecast = self._get_raw_combined_forecast(instrument_code)

        # apply cap
        combined_forecast = post_process_func(raw_multiplied_combined_forecast)
        return combined_forecast

    def _threshold_forecast(self, raw_multiplied_combined_forecast):
        'returns: thresholded forecast'
        def map_forecast_value(x):
            if np.isnan(x):
                return x
            x = float(x)
            if x < -20.0:
                return -30.0
            if x >= -20.0 and x < -10.0:
                return -(abs(x) - 10.0) * 3
            if x >= -10.0 and x <= 10.0:
                return 0.0
            if x > 10.0 and x <= 20.0:
                return (abs(x) - 10.0) * 3
            return 30.0

        combined_forecast = pd.Series(
            [map_forecast_value(x)
                for x in raw_multiplied_combined_forecast.values], raw_multiplied_combined_forecast.index)
        return combined_forecast


if __name__ == '__main__':
    import doctest
    doctest.testmod()
