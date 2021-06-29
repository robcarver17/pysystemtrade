import pandas as pd
from copy import copy

from syscore.pdutils import fix_weights_vs_position_or_forecast, from_dict_of_values_to_df, from_scalar_values_to_ts
from syscore.objects import  resolve_function, missing_data
from syscore.genutils import str2Bool

from sysdata.config.configdata import Config

from sysquant.estimators.turnover import turnoverDataAcrossSubsystems
from sysquant.optimisation.pre_processing import returnsPreProcessor
from sysquant.returns import dictOfReturnsForOptimisationWithCosts, returnsForOptimisationWithCosts

from systems.stage import SystemStage
from systems.system_cache import input, dont_cache, diagnostic, output
from systems.positionsizing import PositionSizing

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
    def get_actual_position(self, instrument_code: str)-> pd.Series:
        """
        Gets the actual position, accounting for cap multiplier

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.Series

        KEY OUTPUT
        """

        self.log.msg(
            "Calculating actual position for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        notional_position = self.get_notional_position(instrument_code)
        cap_multiplier = self.capital_multiplier()
        cap_multiplier = cap_multiplier.reindex(
            notional_position.index).ffill()

        actual_position = notional_position * cap_multiplier

        return actual_position

    @output()
    def get_actual_buffers_for_position(self, instrument_code: str) -> pd.Series:
        """
        Gets the actual buffers for a position, accounting for cap multiplier
        :param instrument_code: instrument to get values for
        :type instrument_code: str
        :returns: Tx1 pd.Series
        KEY OUTPUT
        """

        self.log.msg(
            "Calculating actual buffers for position for %s" % instrument_code,
            instrument_code=instrument_code,
        )


        cap_multiplier = self.capital_multiplier()
        buffers = self.get_buffers_for_position(instrument_code)

        actual_buffers_for_position = _calculate_actual_buffers(buffers,
                                                                cap_multiplier)

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
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_buffers_for_position("EDOLLAR").tail(2)
                     top_pos   bot_pos
        2015-12-10  1.195567  0.978191
        2015-12-11  1.679435  1.374083
        """


        position = self.get_notional_position(instrument_code)
        buffer = self.get_buffers(instrument_code)

        pos_buffers = _apply_buffers_to_position(position = position,
                                                 buffer=buffer)

        return pos_buffers

    @diagnostic()
    def get_buffers(self, instrument_code: str) -> pd.Series:

        self.log.msg(
            "Calculating buffers for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        buffer_method = self.config.buffer_method

        if buffer_method == "forecast":
            buffer = self.get_forecast_method_buffer(instrument_code)
        elif buffer_method == "position":
            buffer = self.get_position_method_buffer(instrument_code)
        else:
            self.log.critical(
                "Buffer method %s not recognised - not buffering" %
                buffer_method)
            buffer = self._get_buffer_if_not_buffering(instrument_code)

        return buffer


    @diagnostic()
    def get_forecast_method_buffer(self, instrument_code: str) -> pd.Series:
        """
        Gets the buffers for positions, using proportion of average forecast method


        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_forecast_method_buffer("EDOLLAR").tail(2)
                      buffer
        2015-12-10  0.671272
        2015-12-11  0.619976
        """

        self.log.msg(
            "Calculating forecast method buffers for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        buffer_size = self.config.buffer_size
        position = self.get_notional_position(instrument_code)

        idm = self.get_instrument_diversification_multiplier()
        instr_weights = self.get_instrument_weights()
        vol_scalar = self.get_volatility_scalar(instrument_code)
        inst_weight_this_code = instr_weights[instrument_code]

        buffer= _calculate_forecast_buffer_method(buffer_size=buffer_size,
                                                  position=position,
                                                  idm=idm,
                                                  inst_weight_this_code=inst_weight_this_code,
                                                  vol_scalar=vol_scalar)

        return buffer

    @diagnostic()
    def get_position_method_buffer(self, instrument_code: str) -> pd.Series:
        """
        Gets the buffers for positions, using proportion of position method

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_position_method_buffer("EDOLLAR").tail(2)
                      buffer
        2015-12-10  0.108688
        2015-12-11  0.152676
        """

        self.log.msg(
            "Calculating position method buffer for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        buffer_size = self.config.buffer_size
        position = self.get_notional_position(instrument_code)
        abs_position = abs(position)

        buffer = abs_position * buffer_size

        buffer.columns = ["buffer"]

        return buffer


    @dont_cache
    def _get_buffer_if_not_buffering(self, instrument_code: str) -> pd.Series:
        position = self.get_notional_position(instrument_code)
        max_max_position = float(position.abs().max()) * 10.0
        buffer = pd.Series(
            [max_max_position] * position.shape[0], index=position.index
        )

        return buffer

    ## notional position
    @output()
    def get_notional_position(self, instrument_code: str)-> pd.Series:
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
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_notional_position("EDOLLAR").tail(2)
                         pos
        2015-12-10  1.086879
        2015-12-11  1.526759

        """

        self.log.msg(
            "Calculating notional position for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        # same frequency as subsystem / forecasts
        notional_position_without_idm =\
            self.get_notional_position_without_idm(instrument_code)

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
            subsys_position.index
        ).ffill()

        notional_position_without_idm = subsys_position * inst_weight_this_code_reindexed

        # subsystem frequency
        return notional_position_without_idm


    # IDM
    @dont_cache
    def get_instrument_diversification_multiplier(self) -> pd.Series:

        if self.use_estimated_instrument_div_mult:
            idm= self.get_estimated_instrument_diversification_multiplier()
        else:
            idm= self.get_fixed_instrument_diversification_multiplier()

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
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosEstimated(), account], data, config)
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

        self.log.terse("Calculating instrument div. multiplier")

        # Get some useful stuff from the config
        div_mult_params = copy(self.config.instrument_div_mult_estimate)

        idm_func = resolve_function(div_mult_params.pop("func"))

        # annual
        correlation_list_object = self.get_instrument_correlation_matrix()

        # daily
        weight_df = self.get_instrument_weights()

        ts_idm = idm_func(
            correlation_list_object,
            weight_df,
            **div_mult_params)

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
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_instrument_diversification_multiplier().tail(2)
                    idm
        2015-12-10  1.2
        2015-12-11  1.2
        >>>
        >>> ## from defaults
        >>> del(config.instrument_div_multiplier)
        >>> system2=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>> system2.portfolio.get_instrument_diversification_multiplier().tail(2)
                    idm
        2015-12-10    1
        2015-12-11    1
        """


        div_mult = self.config.instrument_div_multiplier

        self.log.terse("Using fixed diversification multiplier %f" % div_mult)

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
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosEstimated(), account], data, config)
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

        self.log.terse("Calculating instrument correlations")

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
        daily_unsmoothed_instrument_weights = self.get_unsmoothed_instrument_weights_fitted_to_position_lengths()

        # smooth to avoid jumps when they change
        instrument_weights = daily_unsmoothed_instrument_weights.ewm(smooth_weighting).mean()

        # daily

        return instrument_weights

    @diagnostic()
    def get_unsmoothed_instrument_weights_fitted_to_position_lengths(self) -> pd.DataFrame:
        raw_instrument_weights = self.get_unsmoothed_raw_instrument_weights()

        instrument_list = list(raw_instrument_weights.columns)

        subsystem_positions = [
            self.get_subsystem_position(instrument_code)
            for instrument_code in instrument_list
        ]

        subsystem_positions = pd.concat(subsystem_positions, axis=1).ffill()
        subsystem_positions.columns = instrument_list

        ## this should remove when have NAN's
        ## FIXME CHECK

        instrument_weights = fix_weights_vs_position_or_forecast(
            raw_instrument_weights, subsystem_positions)

        # now on same frequency as positions
        # Move to daily for space saving and so smoothing makes sense
        daily_unsmoothed_instrument_weights = instrument_weights.resample("1B").mean()

        return daily_unsmoothed_instrument_weights


    @diagnostic()
    def get_unsmoothed_raw_instrument_weights(self) -> pd.DataFrame:
        self.log.terse("Calculating instrument weights")

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
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_instrument_weights().tail(2)
                    EDOLLAR  US10
        2015-12-10      0.1   0.9
        2015-12-11      0.1   0.9
        >>>
        >>> del(config.instrument_weights)
        >>> system2=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>> system2.portfolio.get_instrument_weights().tail(2)
        WARNING: No instrument weights  - using equal weights of 0.3333 over all 3 instruments in data
                        BUND   EDOLLAR      US10
        2015-12-10  0.333333  0.333333  0.333333
        2015-12-11  0.333333  0.333333  0.333333
        """

        self.log.msg("Calculating raw instrument weights")

        try:
            instrument_weights_dict = self.config.instrument_weights
        except:
            instrument_weights_dict = self.get_equal_instrument_weights_dict()

        # Now we have a dict, fixed_weights.
        # Need to turn into a timeseries covering the range of subsystem positions
        instrument_list = self.parent.get_instrument_list()

        subsystem_positions = self._get_all_subsystem_positions()
        position_series_index = subsystem_positions.index

        # CHANGE TO TXN DATAFRAME
        instrument_weights = from_dict_of_values_to_df(instrument_weights_dict,
                                  position_series_index,
                                  columns = instrument_list)

        return instrument_weights

    @dont_cache
    def get_equal_instrument_weights_dict(self) -> dict:
        instruments = self.parent.get_instrument_list()
        weight = 1.0 / len(instruments)

        warn_msg = (
                "WARNING: No instrument weights  - using equal weights of %.4f over all %d instruments in data" %
                (weight, len(instruments)))

        self.log.warn(warn_msg)

        instrument_weights = dict(
            [(instrument_code, weight) for instrument_code in instruments]
        )

        return instrument_weights


    @diagnostic()
    def _get_all_subsystem_positions(self) -> pd.DataFrame:
        """

        :return: single pd.matrix of all the positions
        """
        instrument_codes = self.parent.get_instrument_list()

        positions = [self.get_subsystem_position(
            instr_code) for instr_code in instrument_codes]
        positions = pd.concat(positions, axis=1)
        positions.columns = instrument_codes

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
        >>> system=System([account, rawdata, rules, posobject, combobject, capobject,PortfoliosEstimated()], data, config)
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
        return optimiser.weights()



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

        self.log.terse("Calculating raw instrument weights")

        weight_func = weighting_func(
            returns_pre_processor,
            log=self.log,
            **weighting_params)

        return weight_func

    @diagnostic(not_pickable=True)
    def returns_pre_processor(self)  -> returnsPreProcessor:

        pandl_across_subsystems_raw = self.pandl_across_subsystems()
        pandl_across_subsystems_as_returns_object = returnsForOptimisationWithCosts(pandl_across_subsystems_raw)
        pandl_across_subsystems = dictOfReturnsForOptimisationWithCosts(pandl_across_subsystems_as_returns_object)

        turnovers = self.turnover_across_subsystems()
        config = self.config

        weighting_params = copy(config.instrument_weight_estimate)

        returns_pre_processor = returnsPreProcessor(pandl_across_subsystems,
                                                    turnovers = turnovers,
                                                    log=self.log,
                                                    **weighting_params)

        return returns_pre_processor




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
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_subsystem_position("EDOLLAR").tail(2)
                    ss_position
        2015-12-10     1.811465
        2015-12-11     2.544598

        """

        return self.position_size_stage.get_subsystem_position(instrument_code)


    @input
    def pandl_across_subsystems(self) -> pd.DataFrame:
        """
        Return profitability of each instrument

        KEY INPUT

        :param instrument_code:
        :type str:

        :returns: accountCurveGroup object
        """

        accounts = self.accounts_stage

        if accounts is missing_data:
            error_msg = "You need an accounts stage in the system to estimate instrument weights or IDM"
            self.log.critical(error_msg)
            raise Exception(error_msg)

        return accounts.pandl_across_subsystems()

    @input
    def turnover_across_subsystems(self) -> turnoverDataAcrossSubsystems:

        instrument_list = self.parent.get_instrument_list()
        turnover_as_list = [self.accounts_stage.subsystem_turnover(instrument_code)
                            for instrument_code in instrument_list]

        turnover_as_dict = dict([
            (instrument_code, turnover)
            for (instrument_code, turnover)
            in zip(instrument_list, turnover_as_list)
        ])

        turnovers = turnoverDataAcrossSubsystems(turnover_as_dict)

        return turnovers


    @input
    def get_volatility_scalar(self, instrument_code: str) -> pd.Series:
        """
        Get the vol scalar, from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx1 pd.DataFrame

        KEY INPUT

        >>> from systems.tests.testdata import get_test_object_futures_with_pos_sizing
        >>> from systems.basesystem import System
        >>> (posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_pos_sizing()
        >>> system=System([rawdata, rules, posobject, combobject, capobject,PortfoliosFixed()], data, config)
        >>>
        >>> ## from config
        >>> system.portfolio.get_volatility_scalar("EDOLLAR").tail(2)
                    vol_scalar
        2015-12-10   11.187869
        2015-12-11   10.332930
        """

        return self.position_size_stage.get_volatility_scalar(instrument_code)

    @input
    def capital_multiplier(self):
        accounts_stage = self.accounts_stage
        if accounts_stage is missing_data:
            msg ="If using capital_multiplier to work out actual positions, need an accounts module"
            self.log.critical(
                msg
            )
            raise Exception(msg)
        else:
            return accounts_stage.capital_multiplier()


    @property
    def accounts_stage(self):
        accounts_stage = getattr(self.parent, "accounts", missing_data)

        return accounts_stage

    @property
    def config(self) -> Config:
        return self.parent.config

    @property
    def position_size_stage(self) -> PositionSizing:
        return self.parent.positionSize



def _calculate_actual_buffers(buffers: pd.DataFrame,
                              cap_multiplier: pd.Series) -> pd.DataFrame:

    cap_multiplier = cap_multiplier.reindex(buffers.index).ffill()
    cap_multiplier = pd.concat([cap_multiplier, cap_multiplier], axis=1)
    cap_multiplier.columns = buffers.columns

    actual_buffers_for_position = buffers * cap_multiplier

    return actual_buffers_for_position

def _apply_buffers_to_position(position: pd.Series,
                               buffer: pd.Series) -> pd.DataFrame:
    top_position = position.ffill() + buffer.ffill()
    bottom_position = position.ffill() - buffer.ffill()

    pos_buffers = pd.concat([top_position, bottom_position], axis=1)
    pos_buffers.columns = ["top_pos", "bot_pos"]

    return pos_buffers


def _calculate_forecast_buffer_method(inst_weight_this_code: pd.Series,
                                      idm: pd.Series,
                                      vol_scalar: pd.Series,
                                      position: pd.Series,
                                      buffer_size: float):

    inst_weight_this_code = inst_weight_this_code.reindex(
        position.index).ffill()
    idm = idm.reindex(position.index).ffill()
    vol_scalar = vol_scalar.reindex(position.index).ffill()

    average_position = abs(vol_scalar * inst_weight_this_code * idm)

    buffer = average_position * buffer_size

    return buffer



if __name__ == "__main__":
    import doctest

    doctest.testmod()
