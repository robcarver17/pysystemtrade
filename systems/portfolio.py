import pandas as pd
import datetime
from copy import copy

from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.exceptions import missingData
from syscore.genutils import str2Bool, list_union
from syscore.pandas.pdutils import (
    from_dict_of_values_to_df,
    from_scalar_values_to_ts,
)
from syscore.pandas.find_data import get_row_of_df_aligned_to_weights_as_dict
from syscore.pandas.strategy_functions import (
    weights_sum_to_one,
    fix_weights_vs_position_or_forecast,
)
from syscore.objects import resolve_function
from syscore.constants import arg_not_supplied

from sysdata.config.configdata import Config

from sysquant.estimators.stdev_estimator import stdevEstimates, seriesOfStdevEstimates
from sysquant.estimators.correlations import (
    correlationEstimate,
    create_boring_corr_matrix,
    CorrelationList,
)
from sysquant.estimators.covariance import (
    covarianceEstimate,
    covariance_from_stdev_and_correlation,
)
from sysquant.estimators.turnover import turnoverDataAcrossSubsystems
from sysquant.portfolio_risk import (
    calc_portfolio_risk_series,
    calc_sum_annualised_risk_given_portfolio_weights,
)
from sysquant.optimisation.pre_processing import returnsPreProcessor
from sysquant.optimisation.weights import portfolioWeights, seriesOfPortfolioWeights

from sysquant.returns import (
    dictOfReturnsForOptimisationWithCosts,
    returnsForOptimisationWithCosts,
)

from systems.buffering import (
    calculate_buffers,
    calculate_actual_buffers,
    apply_buffers_to_position,
)
from systems.stage import SystemStage
from systems.system_cache import input, dont_cache, diagnostic, output
from systems.positionsizing import PositionSizing
from systems.accounts.curves.account_curve_group import accountCurveGroup
from systems.risk_overlay import get_risk_multiplier
from systems.basesystem import get_instrument_weights_from_config

"""
Stage for portfolios

Gets the position, accounts for instrument weights and diversification
multiplier


Note: At this stage we're dealing with a notional, fixed, amount of capital.
     We'll need to work out p&l to scale positions properly
"""


class Portfolios(SystemStage):
    @property
    def name(self):
        return "portfolio"

    # actual positions and buffers
    @output()
    def get_actual_position(self, instrument_code: str) -> pd.Series:
        """
        Gets the actual position, accounting for cap multiplier

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.Series

        KEY OUTPUT
        """

        self.log.debug(
            "Calculating actual position for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        notional_position = self.get_notional_position(instrument_code)
        cap_multiplier = self.capital_multiplier()
        cap_multiplier = cap_multiplier.reindex(notional_position.index).ffill()

        actual_position = notional_position * cap_multiplier

        return actual_position

    @output()
    def get_actual_buffers_for_position(self, instrument_code: str) -> pd.DataFrame:
        """
        Gets the actual buffers for a position, accounting for cap multiplier
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        :returns: Tx1 pd.Series
        KEY OUTPUT
        """

        self.log.debug(
            "Calculating actual buffers for position for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        cap_multiplier = self.capital_multiplier()
        buffers = self.get_buffers_for_position(instrument_code)

        actual_buffers_for_position = calculate_actual_buffers(buffers, cap_multiplier)

        return actual_buffers_for_position

    # buffers
    @output()
    def get_buffers_for_position(self, instrument_code: str) -> pd.DataFrame:
        """
        Gets the buffers for positions, using method depending on config.buffer_method

        KEY OUTPUT

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx2 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,Portfolios()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_buffers_for_position("EDOLLAR").tail(2)
                     top_pos   bot_pos
        2015-12-10  1.195567  0.978191
        2015-12-11  1.679435  1.374083
        """

        position = self.get_notional_position(instrument_code)
        buffer = self.get_buffers(instrument_code)

        pos_buffers = apply_buffers_to_position(position=position, buffer=buffer)

        return pos_buffers

    @diagnostic()
    def get_buffers(self, instrument_code: str) -> pd.Series:
        position = self.get_notional_position(instrument_code)
        vol_scalar = self.get_average_position_at_subsystem_level(instrument_code)
        log = self.log
        config = self.config
        idm = self.get_instrument_diversification_multiplier()
        instr_weights = self.get_instrument_weights()

        buffer = calculate_buffers(
            instrument_code=instrument_code,
            position=position,
            log=log,
            config=config,
            idm=idm,
            instr_weights=instr_weights,
            vol_scalar=vol_scalar,
        )

        return buffer

    ## notional position
    @output()
    def get_notional_position(self, instrument_code: str) -> pd.Series:
        """
        Gets the position, accounts for instrument weights and diversification multiplier

        Note: At this stage we're dealing with a notional, fixed, amount of capital.
             We'll need to work out p&l to scale positions properly

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY OUTPUT
        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,Portfolios()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_notional_position("EDOLLAR").tail(2)
                         pos
        2015-12-10  1.086879
        2015-12-11  1.526759

        """

        self.log.debug(
            "Calculating notional position for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        # same frequency as subsystem / forecasts
        notional_position_without_risk_scalar = (
            self.get_notional_position_before_risk_scaling(instrument_code)
        )

        try:
            risk_scalar = self.get_risk_scalar()
        except missingData:
            self.log.debug("No risk overlay in config: won't apply risk scaling")
            notional_position = notional_position_without_risk_scalar
        else:
            risk_scalar_reindex = risk_scalar.reindex(
                notional_position_without_risk_scalar.index
            )
            notional_position = (
                notional_position_without_risk_scalar * risk_scalar_reindex.ffill()
            )

        return notional_position

    ## notional position
    @diagnostic()
    def get_notional_position_before_risk_scaling(
        self, instrument_code: str
    ) -> pd.Series:
        """ """

        # same frequency as subsystem / forecasts
        notional_position_without_idm = self.get_notional_position_without_idm(
            instrument_code
        )

        ## daily
        idm = self.get_instrument_diversification_multiplier()
        idm_reindexed = idm.reindex(notional_position_without_idm.index).ffill()

        notional_position = notional_position_without_idm * idm_reindexed

        # same frequency as subsystem / forecasts
        return notional_position

    @diagnostic()
    def get_notional_position_without_idm(self, instrument_code: str) -> pd.Series:
        instr_weights = self.get_instrument_weights()

        # unknown frequency
        subsys_position = self.get_subsystem_position(instrument_code)

        # daily
        instrument_weight_this_code = instr_weights[instrument_code]

        inst_weight_this_code_reindexed = instrument_weight_this_code.reindex(
            subsys_position.index, method="ffill"
        )

        notional_position_without_idm = (
            subsys_position * inst_weight_this_code_reindexed
        )

        # subsystem frequency
        return notional_position_without_idm

    # IDM
    @dont_cache
    def get_instrument_diversification_multiplier(self) -> pd.Series:
        if self.use_estimated_instrument_div_mult:
            idm = self.get_estimated_instrument_diversification_multiplier()
        else:
            idm = self.get_fixed_instrument_diversification_multiplier()

        return idm

    @property
    def use_estimated_instrument_div_mult(self) -> bool:
        """
        It will determine if we use an estimate or a fixed class of object
        """
        return str2Bool(self.config.use_instrument_div_mult_estimates)

    @diagnostic()
    def get_estimated_instrument_diversification_multiplier(self) -> pd.Series:
        """

        Estimate the diversification multiplier for the portfolio

        Estimated from correlations and weights

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing_estimates
        >>> from systems.basesystem import System
        >>> (account, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing_estimates()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,Portfolios(), account], data, config)
        >>> system.config.forecast_weight_estimate["method"]="shrinkage" ## speed things up
        >>> system.config.forecast_weight_estimate["date_method"]="in_sample" ## speed things up
        >>> system.config.instrument_weight_estimate["date_method"]="in_sample" ## speed things up
        >>> system.config.instrument_weight_estimate["method"]="shrinkage" ## speed things up
        >>> system.portfolio.get_instrument_diversification_multiplier().tail(3)
                         IDM
        2015-12-09  1.133220
        2015-12-10  1.133186
        2015-12-11  1.133153
        """

        self.log.info("Calculating instrument div. multiplier")

        # Get some useful stuff from the config
        div_mult_params = copy(self.config.instrument_div_mult_estimate)

        idm_func = resolve_function(div_mult_params.pop("func"))

        # annual
        correlation_list = self.get_instrument_correlation_matrix()

        # daily
        weight_df = self.get_instrument_weights()

        ts_idm = idm_func(correlation_list, weight_df, **div_mult_params)

        # daily

        return ts_idm

    @diagnostic()
    def get_fixed_instrument_diversification_multiplier(self) -> pd.Series:
        """
        Get the instrument diversification multiplier

        :returns: TxK pd.DataFrame containing weights, columns are instrument names, T covers all subsystem positions

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,Portfolios()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_instrument_diversification_multiplier().tail(2)
                    idm
        2015-12-10  1.2
        2015-12-11  1.2
        >>>
        >>> ## from defaults
        >>> del(config.instrument_div_multiplier)
        >>> system2=System([rawdata, rules, posobject, combobject, capobject,Portfolios()], data, config)
        >>> system2.portfolio.get_instrument_diversification_multiplier().tail(2)
                    idm
        2015-12-10    1
        2015-12-11    1
        """

        div_mult = self.config.instrument_div_multiplier

        self.log.info("Using fixed diversification multiplier %f" % div_mult)

        # Now we have a fixed weight
        # Need to turn into a two row timeseries covering the range of forecast
        # dates

        weight_ts = self.get_instrument_weights().index

        ts_idm = from_scalar_values_to_ts(div_mult, weight_ts)

        return ts_idm

    # CORRELATIONS USED FOR IDM

    @diagnostic(protected=True, not_pickable=True)
    def get_instrument_correlation_matrix(self):
        """
        Returns a correlationList object which contains a history of correlation matricies

        :returns: correlation_list object

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing_estimates
        >>> from systems.basesystem import System
        >>> (account, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing_estimates()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,Portfolios(), account], data, config)
        >>> system.config.forecast_weight_estimate["method"]="shrinkage" ## speed things up
        >>> system.config.forecast_weight_estimate["date_method"]="in_sample" ## speed things up
        >>> system.config.instrument_weight_estimate["date_method"]="in_sample" ## speed things up
        >>> system.config.instrument_weight_estimate["method"]="shrinkage" ## speed things up
        >>> ans=system.portfolio.get_instrument_correlation_matrix()
        >>> ans.corr_list[-1]
        array([[ 1.        ,  0.56981346,  0.62458477],
               [ 0.56981346,  1.        ,  0.88087893],
               [ 0.62458477,  0.88087893,  1.        ]])
        >>> print(ans.corr_list[0])
        [[ 1.    0.99  0.99]
         [ 0.99  1.    0.99]
         [ 0.99  0.99  1.  ]]
        >>> print(ans.corr_list[10])
        [[ 1.          0.99        0.99      ]
         [ 0.99        1.          0.78858156]
         [ 0.99        0.78858156  1.        ]]
        """

        self.log.info("Calculating instrument correlations")

        config = self.config

        # Get some useful stuff from the config
        corr_params = copy(config.instrument_correlation_estimate)

        # which function to use for calculation
        corr_func = resolve_function(corr_params.pop("func"))

        pandl = self.pandl_across_subsystems().to_frame()

        return corr_func(pandl, **corr_params)

    ## INSTRUMENT WEIGHTS

    @diagnostic()
    def get_instrument_weights(self) -> pd.DataFrame:
        """
        Get the time series of instrument weights, accounting for potentially missing positions, and weights that don't add up.

        :returns: TxK pd.DataFrame containing weights, columns are instrument names, T covers all subsystem positions


        """

        smooth_weighting = self.config.instrument_weight_ewma_span
        daily_unsmoothed_instrument_weights = (
            self.get_unsmoothed_instrument_weights_fitted_to_position_lengths()
        )

        # smooth to avoid jumps when they change
        smoothed_instrument_weights = daily_unsmoothed_instrument_weights.ewm(
            span=smooth_weighting
        ).mean()

        normalised_smoothed_instrument_weights = weights_sum_to_one(
            smoothed_instrument_weights
        )

        # daily

        return normalised_smoothed_instrument_weights

    @diagnostic()
    def get_unsmoothed_instrument_weights_fitted_to_position_lengths(
        self,
    ) -> pd.DataFrame:
        raw_instrument_weights = self.get_unsmoothed_raw_instrument_weights()

        instrument_list = list(raw_instrument_weights.columns)

        subsystem_positions = self.get_subsystem_positions_for_instrument_list(
            instrument_list
        )

        ## this should remove when have NAN's
        ## FIXME CHECK

        instrument_weights = fix_weights_vs_position_or_forecast(
            raw_instrument_weights, subsystem_positions
        )

        # now on same frequency as positions
        # Move to daily for space saving and so smoothing makes sense
        daily_unsmoothed_instrument_weights = instrument_weights.resample("1B").mean()

        return daily_unsmoothed_instrument_weights

    @diagnostic()
    def get_subsystem_positions_for_instrument_list(
        self, instrument_list: list
    ) -> pd.DataFrame:
        subsystem_positions = [
            self.get_subsystem_position(instrument_code)
            for instrument_code in instrument_list
        ]

        subsystem_positions = pd.concat(subsystem_positions, axis=1).ffill()
        subsystem_positions.columns = instrument_list

        return subsystem_positions

    @diagnostic()
    def get_unsmoothed_raw_instrument_weights(self) -> pd.DataFrame:
        self.log.info("Calculating instrument weights")

        if self.use_estimated_instrument_weights():
            ## will probably be annnual
            raw_instrument_weights = self.get_raw_estimated_instrument_weights()
        else:
            ## will be 2*N
            raw_instrument_weights = self.get_raw_fixed_instrument_weights()

        return raw_instrument_weights

    @input
    def use_estimated_instrument_weights(self):
        """
        It will determine if we use an estimate or a fixed class of object
        """
        return str2Bool(self.parent.config.use_instrument_weight_estimates)

    ## FIXED INSTRUMENT WEIGHTS
    @diagnostic()
    def get_raw_fixed_instrument_weights(self) -> pd.DataFrame:
        """
        Get the instrument weights
        These are 'raw' because we need to account for potentially missing positions, and weights that don't add up.
        From: (a) passed into subsystem when created
              (b) ... if not found then: in system.config.instrument_weights
        :returns: TxK pd.DataFrame containing weights, columns are instrument names, T covers all subsystem positions
        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> config.instrument_weights=dict(EDOLLAR=0.1, US10=0.9)
        >>> system=System([rawdata, rules, posobject, combobject, capobject,Portfolios()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_instrument_weights().tail(2)
                    EDOLLAR  US10
        2015-12-10      0.1   0.9
        2015-12-11      0.1   0.9
        >>>
        >>> del(config.instrument_weights)
        >>> system2=System([rawdata, rules, posobject, combobject, capobject,Portfolios()], data, config)
        >>> system2.portfolio.get_instrument_weights().tail(2)
        WARNING: No instrument weights  - using equal weights of 0.3333 over all 3 instruments in data
                        BUND   EDOLLAR      US10
        2015-12-10  0.333333  0.333333  0.333333
        2015-12-11  0.333333  0.333333  0.333333
        """

        self.log.debug("Calculating raw instrument weights")
        instrument_weights_dict = self.get_fixed_instrument_weights_from_config()

        # Now we have a dict, fixed_weights.
        # Need to turn into a timeseries covering the range of subsystem positions
        instrument_list = self.get_instrument_list()

        subsystem_positions = self._get_all_subsystem_positions()
        position_series_index = subsystem_positions.index

        # CHANGE TO TXN DATAFRAME
        instrument_weights = from_dict_of_values_to_df(
            instrument_weights_dict, position_series_index, columns=instrument_list
        )

        return instrument_weights

    @diagnostic()
    def get_fixed_instrument_weights_from_config(self) -> dict:
        try:
            instrument_weights_dict = get_instrument_weights_from_config(self.config)
        except:
            instrument_weights_dict = self.get_equal_instrument_weights_dict()

        instrument_weights_dict = self._add_zero_instrument_weights(
            instrument_weights_dict
        )

        return instrument_weights_dict

    @dont_cache
    def get_equal_instrument_weights_dict(self) -> dict:
        instruments_with_weights = self.get_instrument_list(for_instrument_weights=True)
        weight = 1.0 / len(instruments_with_weights)

        warn_msg = (
            "WARNING: No instrument weights  - using equal weights of %.4f over all %d instruments in data"
            % (weight, len(instruments_with_weights))
        )

        self.log.warning(warn_msg)

        instrument_weights = dict(
            [(instrument_code, weight) for instrument_code in instruments_with_weights]
        )

        return instrument_weights

    def _add_zero_instrument_weights(self, instrument_weights: dict) -> dict:
        copy_instrument_weights = copy(instrument_weights)
        instruments_with_zero_weights = (
            self.allocate_zero_instrument_weights_to_these_instruments()
        )
        for instrument_code in instruments_with_zero_weights:
            copy_instrument_weights[instrument_code] = 0.0

        return copy_instrument_weights

    def _remove_zero_weighted_instruments_from_df(
        self, some_data_frame: pd.DataFrame
    ) -> pd.DataFrame:
        copy_df = copy(some_data_frame)
        instruments_with_zero_weights = (
            self.allocate_zero_instrument_weights_to_these_instruments()
        )
        copy_df.drop(labels=instruments_with_zero_weights)

        return copy_df

    ## INPUT
    @diagnostic()
    def _get_all_subsystem_positions(self) -> pd.DataFrame:
        """

        :return: single pd.matrix of all the positions
        """
        instrument_list = self.get_instrument_list()

        positions = self.get_subsystem_positions_for_instrument_list(instrument_list)

        return positions

    ## ESTIMATED WEIGHTS
    @diagnostic()
    def get_raw_estimated_instrument_weights(self) -> pd.DataFrame:
        """
        Estimate the instrument weights


        :returns: TxK pd.DataFrame containing weights, columns are trading rule variation names, T covers all

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing_estimates
        >>> from systems.basesystem import System
        >>> (account, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing_estimates()
        >>> system=System([account, rawdata, rules, posobject, combobject, capobject,Portfolios()], data, config)
        >>> system.config.forecast_weight_estimate["method"]="shrinkage" ## speed things up
        >>> system.config.forecast_weight_estimate["date_method"]="in_sample" ## speed things up
        >>> system.config.instrument_weight_estimate["method"]="shrinkage"
        >>> system.portfolio.get_raw_instrument_weights().tail(3)
                            BUND   EDOLLAR      US10
        2015-05-30  4.006172e-17  0.499410  0.500590
        2015-06-01  5.645388e-01  0.217462  0.217999
        2015-12-12  5.645388e-01  0.217462  0.217999
        """

        # these will probably be annual
        optimiser = self.calculation_of_raw_instrument_weights()
        weights_of_instruments_with_weights = optimiser.weights()

        instrument_weights = self._add_zero_weights_to_instrument_weights_df(
            weights_of_instruments_with_weights
        )

        return instrument_weights

    def fit_periods(self):
        # FIXME, NO GUARANTEE THIS OBJECT HAS AN ESTIMATOR UNLESS IT INHERITS FROM
        # SOME KIND OF BASECLASS

        weight_calculator = self.calculation_of_raw_instrument_weights()

        return weight_calculator.fit_dates

    @diagnostic()
    def correlation_estimator_for_subsystem_returns(self):
        # FIXME, NO GUARANTEE THIS OBJECT HAS AN ESTIMATOR UNLESS IT INHERITS FROM
        # SOME KIND OF BASECLASS

        weight_calculator = self.calculation_of_raw_instrument_weights()

        return weight_calculator.correlation_estimator

    @diagnostic(protected=True, not_pickable=True)
    def calculation_of_raw_instrument_weights(self):
        """
        Estimate the instrument weights

        Done like this to expose calculations

        :returns: TxK pd.DataFrame containing weights, columns are instrument names, T covers all

        """

        # Get some useful stuff from the config
        weighting_params = copy(self.config.instrument_weight_estimate)

        # which function to use for calculation
        weighting_func = resolve_function(weighting_params.pop("func"))

        returns_pre_processor = self.returns_pre_processor()

        self.log.info("Calculating raw instrument weights")

        weight_func = weighting_func(
            returns_pre_processor, log=self.log, **weighting_params
        )

        return weight_func

    @diagnostic(not_pickable=True)
    def returns_pre_processor(self) -> returnsPreProcessor:
        instrument_list = self.get_instrument_list(for_instrument_weights=True)
        pandl_across_subsystems_raw = self.pandl_across_subsystems(
            instrument_list=instrument_list
        )
        pandl_across_subsystems_as_returns_object = returnsForOptimisationWithCosts(
            pandl_across_subsystems_raw
        )
        pandl_across_subsystems = dictOfReturnsForOptimisationWithCosts(
            pandl_across_subsystems_as_returns_object
        )

        turnovers = self.turnover_across_subsystems()
        config = self.config

        weighting_params = copy(config.instrument_weight_estimate)

        returns_pre_processor = returnsPreProcessor(
            pandl_across_subsystems,
            turnovers=turnovers,
            log=self.log,
            **weighting_params,
        )

        return returns_pre_processor

    def _add_zero_weights_to_instrument_weights_df(
        self, instrument_weights: pd.DataFrame
    ) -> pd.DataFrame:
        instrument_list_to_add = (
            self.allocate_zero_instrument_weights_to_these_instruments()
        )
        weight_index = instrument_weights.index
        new_pd_as_dict = dict(
            [
                (instrument_code, pd.Series([0.0] * len(weight_index)))
                for instrument_code in instrument_list_to_add
            ]
        )
        new_pd = pd.DataFrame(new_pd_as_dict)

        padded_instrument_weights = pd.concat([instrument_weights, new_pd], axis=1)

        return padded_instrument_weights

    @diagnostic()
    def allocate_zero_instrument_weights_to_these_instruments(
        self, auto_remove_bad_instruments: bool = False
    ) -> list:
        config_allocate_zero_instrument_weights_to_these_instruments = (
            self.config_allocates_zero_instrument_weights_to_these_instruments(
                auto_remove_bad_instruments=auto_remove_bad_instruments
            )
        )

        instruments_without_data_or_weights = self.instruments_without_data_or_weights()

        all_instruments_to_allocate_zero_to = list_union(
            instruments_without_data_or_weights,
            config_allocate_zero_instrument_weights_to_these_instruments,
        )

        return all_instruments_to_allocate_zero_to

    def config_allocates_zero_instrument_weights_to_these_instruments(
        self, auto_remove_bad_instruments: bool = False
    ):
        bad_from_config = self.parent.get_list_of_markets_not_trading_but_with_data()
        config = self.config
        config_allocates_zero_instrument_weights_to_these_instruments = getattr(
            config, "allocate_zero_instrument_weights_to_these_instruments", []
        )
        instrument_list = self.get_instrument_list()
        config_marks_bad_and_in_instrument_list = list(
            set(instrument_list).intersection(set(bad_from_config))
        )
        configured_bad_but_not_configured_zero_allocation = list(
            set(config_marks_bad_and_in_instrument_list).difference(
                set(config_allocates_zero_instrument_weights_to_these_instruments)
            )
        )

        allocate_zero_instrument_weights_to_these_instruments = copy(
            config_allocates_zero_instrument_weights_to_these_instruments
        )
        if len(configured_bad_but_not_configured_zero_allocation) > 0:
            if auto_remove_bad_instruments:
                self.log.warning(
                    "*** Following instruments are listed as trading_restrictions and/or bad_markets and will be removed from instrument weight optimisation: ***\n%s"
                    % str(configured_bad_but_not_configured_zero_allocation)
                )
                allocate_zero_instrument_weights_to_these_instruments = (
                    allocate_zero_instrument_weights_to_these_instruments
                    + configured_bad_but_not_configured_zero_allocation
                )
            else:
                self.log.warning(
                    "*** Following instruments are listed as trading_restrictions and/or bad_markets but still included in instrument weight optimisation: ***\n%s"
                    % str(configured_bad_but_not_configured_zero_allocation)
                )
                self.log.warning(
                    "This is fine for dynamic systems where we remove them in later optimisation, but may be problematic for static systems"
                )
                self.log.warning(
                    "Consider adding to config element allocate_zero_instrument_weights_to_these_instruments"
                )

        if len(allocate_zero_instrument_weights_to_these_instruments) > 0:
            self.log.debug(
                "Following instruments will have zero weight in optimisation of instrument weights as configured zero or auto removal of configured bad%s"
                % str(allocate_zero_instrument_weights_to_these_instruments)
            )

        return allocate_zero_instrument_weights_to_these_instruments

    def instruments_without_data_or_weights(self) -> list:
        subsystem_positions = copy(self._get_all_subsystem_positions())
        subsystem_positions[subsystem_positions.isna()] = 0
        not_zero = subsystem_positions != 0
        index_of_empty_markets = not_zero.sum(axis=0) == 0
        list_of_empty_markets = [
            instrument_code
            for instrument_code, empty in index_of_empty_markets.items()
            if empty
        ]

        self.log.debug(
            "Following instruments will have zero weight in optimisation of instrument weights as they have no positions (possibly too expensive?) %s"
            % str(list_of_empty_markets)
        )

        return list_of_empty_markets

    @input
    def get_subsystem_position(self, instrument_code: str) -> pd.Series:
        """
        Get the position assuming all capital in one position, from a previous
        module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,Portfolios()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_subsystem_position("EDOLLAR").tail(2)
                    ss_position
        2015-12-10     1.811465
        2015-12-11     2.544598

        """

        return self.position_size_stage.get_subsystem_position(instrument_code)

    @input
    def pandl_across_subsystems(
        self, instrument_list: list = arg_not_supplied
    ) -> accountCurveGroup:
        """
        Return profitability of each instrument

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: accountCurveGroup object
        """

        try:
            accounts = self.accounts_stage
        except missingData as e:
            error_msg = "You need an accounts stage in the system to estimate instrument weights or IDM"
            self.log.critical(error_msg)
            raise missingData(error_msg) from e

        if instrument_list is arg_not_supplied:
            instrument_list = self.get_instrument_list()

        ## roundpositions=True required to make IDM work with order simulator
        return accounts.pandl_across_subsystems_given_instrument_list(
            instrument_list, roundpositions=True
        )

    @input
    def turnover_across_subsystems(self) -> turnoverDataAcrossSubsystems:
        instrument_list = self.get_instrument_list(for_instrument_weights=True)
        turnover_as_list = [
            self.accounts_stage.subsystem_turnover(instrument_code)
            for instrument_code in instrument_list
        ]

        turnover_as_dict = dict(
            [
                (instrument_code, turnover)
                for (instrument_code, turnover) in zip(
                    instrument_list, turnover_as_list
                )
            ]
        )

        turnovers = turnoverDataAcrossSubsystems(turnover_as_dict)

        return turnovers

    @input
    def get_average_position_at_subsystem_level(
        self, instrument_code: str
    ) -> pd.Series:
        """
        Get the vol scalar, from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,Portfolios
        ()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_average_position_at_subsystem_level("EDOLLAR").tail(2)
                    vol_scalar
        2015-12-10   11.187869
        2015-12-11   10.332930
        """

        return self.position_size_stage.get_average_position_at_subsystem_level(
            instrument_code
        )

    @input
    def capital_multiplier(self):
        try:
            accounts_stage = self.accounts_stage
        except missingData as e:
            msg = "If using capital_multiplier to work out actual positions, need an accounts module"
            self.log.critical(msg)
            raise missingData(msg) from e
        else:
            return accounts_stage.capital_multiplier()

    ## RISK
    @diagnostic()
    def get_risk_scalar(self) -> pd.Series:
        risk_overlay_config = self.config.get_element("risk_overlay")

        normal_risk = self.get_portfolio_risk_for_original_positions()
        shocked_vol_risk = (
            self.get_portfolio_risk_for_original_positions_with_shocked_vol()
        )
        sum_abs_risk = self.get_sum_annualised_risk_for_original_positions()
        leverage = self.get_leverage_for_original_position()
        percentage_vol_target = self.get_percentage_vol_target()

        risk_scalar = get_risk_multiplier(
            risk_overlay_config=risk_overlay_config,
            normal_risk=normal_risk,
            shocked_vol_risk=shocked_vol_risk,
            sum_abs_risk=sum_abs_risk,
            leverage=leverage,
            percentage_vol_target=percentage_vol_target,
        )

        return risk_scalar

    @diagnostic()
    def get_leverage_for_original_position(self) -> pd.Series:
        portfolio_weights = self.get_original_portfolio_weight_df()
        leverage = portfolio_weights.get_sum_leverage()

        return leverage

    @diagnostic()
    def get_sum_annualised_risk_for_original_positions(
        self,
    ) -> pd.Series:
        portfolio_weights = self.get_original_portfolio_weight_df()
        return self.get_sum_annualised_risk_given_portfolio_weights(portfolio_weights)

    def get_sum_annualised_risk_given_portfolio_weights(
        self,
        portfolio_weights: seriesOfPortfolioWeights,
    ) -> pd.Series:
        pd_of_stdev = self.get_stdev_df()
        risk_series = calc_sum_annualised_risk_given_portfolio_weights(
            portfolio_weights=portfolio_weights, pd_of_stdev=pd_of_stdev
        )

        return risk_series

    @diagnostic()
    def get_portfolio_risk_for_original_positions(self) -> pd.Series:
        weights = self.get_original_portfolio_weight_df()
        return self.get_portfolio_risk_given_weights(weights)

    @diagnostic()
    def get_portfolio_risk_for_original_positions_with_shocked_vol(self) -> pd.Series:
        weights = self.get_original_portfolio_weight_df()
        return self.get_portfolio_risk_given_weights(weights, use_shocked_vol=True)

    def get_portfolio_risk_given_weights(
        self, portfolio_weights: seriesOfPortfolioWeights, use_shocked_vol=False
    ) -> pd.Series:
        list_of_correlations = self.get_list_of_instrument_returns_correlations()
        pd_of_stdev = self.get_stdev_df(shocked=use_shocked_vol)
        risk_series = calc_portfolio_risk_series(
            portfolio_weights=portfolio_weights,
            list_of_correlations=list_of_correlations,
            pd_of_stdev=pd_of_stdev,
        )

        return risk_series

    def get_stdev_df(self, shocked: bool = False) -> seriesOfStdevEstimates:
        if shocked:
            return self.get_shocked_df_of_perc_vol()
        else:
            return self.get_df_of_perc_vol()

    @diagnostic()
    def get_shocked_df_of_perc_vol(self) -> seriesOfStdevEstimates:
        df_of_vol = self.get_df_of_perc_vol()
        shocked_df_of_vol = df_of_vol.shocked()

        return shocked_df_of_vol

    ## PORTFOLIO WEIGHTS
    def get_position_contracts_for_relevant_date(
        self, relevant_date: datetime.datetime = arg_not_supplied
    ) -> portfolioWeights:
        position_contracts_as_df = self.get_position_contracts_as_df()
        position_contracts_at_date = get_row_of_df_aligned_to_weights_as_dict(
            position_contracts_as_df, relevant_date
        )

        position_contracts = portfolioWeights(position_contracts_at_date)

        return position_contracts

    def get_covariance_matrix(
        self,
        relevant_date: datetime.datetime = arg_not_supplied,
        correlation_estimation_parameters=arg_not_supplied,
    ) -> covarianceEstimate:
        correlation_estimate = self.get_correlation_matrix(
            relevant_date=relevant_date,
            correlation_estimation_parameters=correlation_estimation_parameters,
        )
        stdev_estimate = self.get_stdev_estimate(relevant_date=relevant_date)

        covariance = covariance_from_stdev_and_correlation(
            correlation_estimate, stdev_estimate
        )

        return covariance

    def get_correlation_matrix(
        self,
        relevant_date: datetime.datetime = arg_not_supplied,
        correlation_estimation_parameters: dict = arg_not_supplied,
    ) -> correlationEstimate:
        list_of_correlations = self.get_list_of_instrument_returns_correlations(
            correlation_estimation_parameters=correlation_estimation_parameters
        )
        try:
            correlation_matrix = (
                list_of_correlations.most_recent_correlation_before_date(relevant_date)
            )
        except:
            instrument_list = self.get_instrument_list()
            correlation_matrix = create_boring_corr_matrix(
                len(instrument_list), columns=instrument_list, offdiag=0.0
            )

        return correlation_matrix

    @diagnostic(not_pickable=True)
    def get_list_of_instrument_returns_correlations(
        self, correlation_estimation_parameters: dict = arg_not_supplied
    ) -> CorrelationList:
        config = self.config
        if correlation_estimation_parameters is arg_not_supplied:
            # Get some useful stuff from the config
            corr_parameters = copy(config.instrument_returns_correlation)
        else:
            corr_parameters = copy(correlation_estimation_parameters)

        # which function to use for calculation
        corr_func = resolve_function(corr_parameters.pop("func"))

        returns_as_pd = self.returns_across_instruments_as_df()

        return corr_func(returns_as_pd, **corr_parameters)

    @diagnostic()
    def returns_across_instruments_as_df(self) -> pd.DataFrame:
        instrument_list = self.get_instrument_list()
        returns_as_dict = dict(
            [
                (
                    instrument_code,
                    self.percentage_return_for_instrument(instrument_code),
                )
                for instrument_code in instrument_list
            ]
        )

        returns_as_pd = pd.DataFrame(returns_as_dict)

        return returns_as_pd

    def percentage_return_for_instrument(self, instrument_code) -> pd.Series:
        return self.rawdata.get_daily_percentage_returns(instrument_code)

    def get_per_contract_value(
        self, relevant_date: datetime.datetime = arg_not_supplied
    ) -> portfolioWeights:
        df_of_values = self.get_per_contract_value_as_proportion_of_capital_df()
        values_at_date = get_row_of_df_aligned_to_weights_as_dict(
            df_of_values, relevant_date
        )
        contract_values = portfolioWeights(values_at_date)

        return contract_values

    def get_stdev_estimate(
        self, relevant_date: datetime.datetime = arg_not_supplied
    ) -> stdevEstimates:
        df_of_vol = self.get_df_of_perc_vol()

        return df_of_vol.get_stdev_on_date(relevant_date)

    @diagnostic()
    def get_df_of_perc_vol(self) -> seriesOfStdevEstimates:
        instrument_list = self.get_instrument_list()
        vol_as_dict = dict(
            [
                (instrument_code, self.annualised_percentage_vol(instrument_code))
                for instrument_code in instrument_list
            ]
        )

        vol_as_pd = pd.DataFrame(vol_as_dict)
        vol_as_pd = vol_as_pd.ffill()

        return seriesOfStdevEstimates(vol_as_pd)

    @diagnostic()
    def common_index(self):
        portfolio_weights = self.get_original_portfolio_weight_df()
        common_index = portfolio_weights.index

        return common_index

    @diagnostic()
    def get_original_portfolio_weight_df(self) -> seriesOfPortfolioWeights:
        instrument_list = self.get_instrument_list()
        weights_as_dict = dict(
            [
                (
                    instrument_code,
                    self.get_portfolio_weight_series_from_contract_positions(
                        instrument_code
                    ),
                )
                for instrument_code in instrument_list
            ]
        )

        weights_as_pd = pd.DataFrame(weights_as_dict)
        weights_as_pd = weights_as_pd.ffill()

        return seriesOfPortfolioWeights(weights_as_pd)

    @diagnostic()
    def get_per_contract_value_as_proportion_of_capital_df(self) -> pd.DataFrame:
        instrument_list = self.get_instrument_list()
        values_as_dict = dict(
            [
                (
                    instrument_code,
                    self.get_per_contract_value_as_proportion_of_capital(
                        instrument_code
                    ),
                )
                for instrument_code in instrument_list
            ]
        )

        values_as_pd = pd.DataFrame(values_as_dict)
        common_index = self.common_index()

        values_as_pd = values_as_pd.reindex(common_index)
        values_as_pd = values_as_pd.ffill()

        ## slight cheating
        values_as_pd = values_as_pd.bfill()

        return values_as_pd

    def get_position_contracts_as_df(self) -> pd.DataFrame:
        instrument_list = self.get_instrument_list()
        values_as_dict = dict(
            [
                (
                    instrument_code,
                    self.get_notional_position_before_risk_scaling(instrument_code),
                )
                for instrument_code in instrument_list
            ]
        )

        values_as_pd = pd.DataFrame(values_as_dict)
        common_index = self.common_index()

        values_as_pd = values_as_pd.reindex(common_index)
        values_as_pd = values_as_pd.ffill()

        return values_as_pd

    @diagnostic()
    def get_portfolio_weight_series_from_contract_positions(
        self, instrument_code: str
    ) -> pd.Series:
        contract_positions = self.get_notional_position_before_risk_scaling(
            instrument_code
        )
        per_contract_value_as_proportion_of_capital = (
            self.get_per_contract_value_as_proportion_of_capital(instrument_code)
        )

        weights_as_proportion_of_capital = get_portfolio_weights_from_contract_positions(
            contract_positions=contract_positions,
            per_contract_value_as_proportion_of_capital=per_contract_value_as_proportion_of_capital,
        )
        return weights_as_proportion_of_capital

    def get_per_contract_value_as_proportion_of_capital(
        self, instrument_code: str
    ) -> pd.Series:
        trading_capital = self.get_trading_capital()
        contract_values = self.get_baseccy_value_per_contract(instrument_code)

        per_contract_value_as_proportion_of_capital = contract_values / trading_capital

        return per_contract_value_as_proportion_of_capital

    def get_baseccy_value_per_contract(self, instrument_code: str) -> pd.Series:
        contract_prices = self.get_contract_prices(instrument_code)
        contract_multiplier = self.get_contract_multiplier(instrument_code)
        fx_rate = self.get_fx_for_contract(instrument_code)

        fx_rate_aligned = fx_rate.reindex(contract_prices.index, method="ffill")

        return fx_rate_aligned * contract_prices * contract_multiplier

    def annualised_percentage_vol(self, instrument_code: str) -> pd.Series:
        daily_vol = self.daily_percentage_vol100scale(instrument_code)
        return ROOT_BDAYS_INYEAR * daily_vol / 100.0

    ## INPUT
    def get_instrument_list(
        self, for_instrument_weights=False, auto_remove_bad_instruments=False
    ) -> list:
        instrument_list = self.parent.get_instrument_list()
        if for_instrument_weights:
            instrument_list = copy(instrument_list)
            allocate_zero_instrument_weights_to_these_instruments = (
                self.allocate_zero_instrument_weights_to_these_instruments(
                    auto_remove_bad_instruments
                )
            )

            for (
                instrument_code_to_remove
            ) in allocate_zero_instrument_weights_to_these_instruments:
                instrument_list.remove(instrument_code_to_remove)

        return instrument_list

    ## INPUTS
    def daily_percentage_vol100scale(self, instrument_code: str) -> pd.Series:
        return self.rawdata.get_daily_percentage_volatility(instrument_code)

    def get_percentage_vol_target(self) -> float:
        return self.position_size_stage.get_percentage_vol_target()

    def get_trading_capital(self) -> float:
        return self.position_size_stage.get_notional_trading_capital()

    def get_contract_prices(self, instrument_code: str) -> pd.Series:
        return self.position_size_stage.get_underlying_price(instrument_code)

    def get_contract_multiplier(self, instrument_code: str) -> float:
        return float(self.data.get_value_of_block_price_move(instrument_code))

    def get_fx_for_contract(self, instrument_code: str) -> pd.Series:
        return self.position_size_stage.get_fx_rate(instrument_code)

    ## stages
    @property
    def rawdata(self):
        return self.parent.rawdata

    @property
    def data(self):
        return self.parent.data

    @property
    def accounts_stage(self):
        try:
            accounts_stage = getattr(self.parent, "accounts")
        except AttributeError as e:
            raise missingData from e

        return accounts_stage

    @property
    def config(self) -> Config:
        return self.parent.config

    @property
    def position_size_stage(self) -> PositionSizing:
        return self.parent.positionSize


def get_portfolio_weights_from_contract_positions(
    contract_positions: pd.Series,
    per_contract_value_as_proportion_of_capital: pd.Series,
) -> pd.Series:
    aligned_values = per_contract_value_as_proportion_of_capital.reindex(
        contract_positions.index, method="ffill"
    )
    weights_as_proportion_of_capital = contract_positions * aligned_values

    return weights_as_proportion_of_capital


if __name__ == "__main__":
    import doctest

    doctest.testmod()
