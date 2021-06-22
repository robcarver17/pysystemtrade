import datetime
from copy import copy

import numpy as np
import pandas as pd

from syscore.genutils import progressBar, str2Bool
from syscore.objects import arg_not_supplied
from syscore.pdutils import get_row_of_df_aligned_to_weights_as_dict, from_series_to_matching_df_frame

from sysquant.estimators.covariance import covarianceEstimate
from sysquant.estimators.mean_estimator import meanEstimates
from sysquant.optimisation.weights import portfolioWeights

from systems.stage import SystemStage
from systems.system_cache import diagnostic

from systems.provided.small_system_optimise.expected_returns import expectedReturnsStage
from systems.provided.small_system_optimise.calculations import maximise_without_discrete_weights, \
    optimise_with_fixed_contract_values


class optimisedPositions(SystemStage):
    @property
    def name(self):
        return "optimisedPositions"

    @diagnostic()
    def get_optimised_position_df(self):
        weights_list_df = self.get_optimised_weights_df()
        per_contract_value_as_proportion_of_df = self.get_per_contract_value_as_proportion_of_capital_df()

        positions = weights_list_df / per_contract_value_as_proportion_of_df

        return positions

    @diagnostic()
    def get_optimised_weights_df(self) -> pd.DataFrame:
        self.log.msg("Optimising positions for small capital: may take a while!")
        common_index = list(self.common_index())
        p = progressBar(len(common_index), show_timings=True, show_each_time=True)
        previous_optimal_weights = portfolioWeights.allzeros(self.instrument_list())
        weights_list = []
        for relevant_date in common_index:
            #self.log.msg(relevant_date)
            optimal_weights = self.get_optimal_weights_with_fixed_contract_values(relevant_date,
                                                                                  previous_weights=previous_optimal_weights)
            weights_list.append(optimal_weights)
            previous_optimal_weights = copy(optimal_weights)
            p.iterate()
        p.finished()
        weights_list_df = pd.DataFrame(weights_list, index=common_index)

        return weights_list_df



    def get_optimal_weights_with_fixed_contract_values(self, relevant_date: datetime.datetime = arg_not_supplied,
                                                       previous_weights: portfolioWeights = arg_not_supplied) -> portfolioWeights:

        covariance_matrix = self.get_covariance_matrix(relevant_date=relevant_date)
        risk_aversion = self.risk_aversion_coefficient()
        expected_returns = self.get_implied_expected_returns(relevant_date)
        per_contract_value = self.get_per_contract_value(relevant_date)
        max_portfolio_weights = self.get_maximum_portfolio_weight_at_date(relevant_date)
        original_portfolio_weights = self.original_portfolio_weights_for_relevant_date(relevant_date)
        max_risk_as_variance = self.get_max_risk_as_variance()

        costs = self.get_costs_per_contract_as_proportion_of_capital_all_instruments()

        use_process_pool = str2Bool(self.config.small_system['use_process_pool'])

        ## split up a bit??
        optimal_weights = optimise_with_fixed_contract_values(per_contract_value=per_contract_value,
                                                              expected_returns=expected_returns,
                                                              risk_aversion=risk_aversion,
                                                              covariance_matrix=covariance_matrix,
                                                              max_portfolio_weights=max_portfolio_weights,
                                                              original_portfolio_weights = original_portfolio_weights,
                                                              max_risk_as_variance = max_risk_as_variance,
                                                              costs = costs,
                                                              previous_weights = previous_weights,
                                                              use_process_pool = use_process_pool)

        return optimal_weights


    def get_max_risk_as_variance(self) -> float:
        max_risk_scalar = self.config.small_system['max_risk_ceiling_as_fraction_normal_risk']
        risk_target = self.risk_target()

        max_risk_ceiling = max_risk_scalar * risk_target
        max_risk_as_variance = max_risk_ceiling**2

        return max_risk_as_variance

    def get_maximum_portfolio_weight_at_date(self,
                                             relevant_date: datetime.datetime = arg_not_supplied) -> portfolioWeights:

        max_portfolio_weight = self.get_maximum_portfolio_weight_as_df()
        max_weight_at_date = get_row_of_df_aligned_to_weights_as_dict(max_portfolio_weight,
                                                                      relevant_date)

        return portfolioWeights(max_weight_at_date)

    ## MAXIMUM PORTFOLIO WEIGHTS FOR OPTIMISATION
    @diagnostic()
    def get_maximum_portfolio_weight_as_df(self) -> pd.DataFrame:
        risk_multiplier = self.get_risk_multiplier_df()
        max_risk_per_instrument = self.get_series_of_maximum_risk_per_instrument()

        ## funky aligntment
        common_index = self.common_index()
        risk_multiplier_aligned = risk_multiplier.reindex(common_index, method="ffill")
        max_risk_per_instrument_aligned_df = \
            from_series_to_matching_df_frame(max_risk_per_instrument,
                risk_multiplier_aligned)

        max_portfolio_weights = risk_multiplier_aligned.ffill() \
                                * max_risk_per_instrument_aligned_df.ffill()
        return max_portfolio_weights

    ## MAXIMUM ALLOWABLE RISK PER INSTRUMENT
    @diagnostic()
    def get_series_of_maximum_risk_per_instrument(self) -> pd.Series:
        ## Given N instruments we have an average of IDM/N
        ## max portfolio weight = Fudge_factor * IDM / N
        ## fudge factor is highest possible instrument weight versus average

        max_instrument_weight = self.get_max_instrument_weight()
        idm = self.get_instrument_diversification_multiplier()
        ratio_of_max_to_average_forecast = self.get_ratio_of_max_to_average_forecast()
        my_config = self.config.small_system['max_risk_per_instrument']

        max_risk_per_instrument = \
            calculate_max_risk_per_instrument(ratio_of_max_to_average_forecast = ratio_of_max_to_average_forecast,
                                                idm = idm,
                                                max_instrument_weight=max_instrument_weight,
                                              my_config = my_config)

        return max_risk_per_instrument


    def get_max_instrument_weight(self) -> pd.Series:
        instrument_weights = self.get_instrument_weights()
        max_instrument_weight = instrument_weights.max(axis=1)

        return max_instrument_weight

    ## RISK MULTIPLIER (relative vol instrument: target)
    def get_risk_multiplier_df(self) -> pd.DataFrame:
        instrument_list = self.instrument_list()
        multiplier_as_dict = dict([
            (instrument_code,
                self.get_risk_multiplier_series(instrument_code))
                           for instrument_code in instrument_list])

        multiplier_as_pd = pd.DataFrame(multiplier_as_dict)
        common_index= self.common_index()
        multiplier_as_pd = multiplier_as_pd.reindex(common_index, method="ffill")

        return multiplier_as_pd

    def get_risk_multiplier_series(self, instrument_code: str) -> pd.Series:

        risk_target = self.risk_target()
        annualised_instrument_stdev = self.annualised_percentage_vol(instrument_code)

        return risk_target / annualised_instrument_stdev

    def risk_target(self) -> float:
        return self.percentage_vol_target()/100.0



    ## COSTS
    @diagnostic()
    def get_costs_per_contract_as_proportion_of_capital_all_instruments(self) -> meanEstimates:
        instrument_list = self.instrument_list()
        costs = dict([
            (instrument_code, self.get_cost_per_contract_as_proportion_of_capital(instrument_code))
            for instrument_code in instrument_list
        ])

        costs = meanEstimates(costs)

        return costs

    def get_cost_per_contract_as_proportion_of_capital(self, instrument_code)-> float:
        cost_per_contract = self.get_cost_per_contract_in_base_ccy(instrument_code)
        trading_capital = self.get_trading_capital()
        cost_multiplier = self.cost_multiplier()

        return cost_multiplier * cost_per_contract / trading_capital

    def cost_multiplier(self) -> float:
        cost_multiplier = float(self.config.small_system['cost_multiplier'])
        return cost_multiplier

    def get_cost_per_contract_in_base_ccy(self, instrument_code: str) -> float:
        raw_cost_data = self.get_raw_cost_data(instrument_code)
        multiplier = self.get_contract_multiplier(instrument_code)
        last_price= self.get_final_price(instrument_code)
        fx_rate = self.get_last_fx_rate(instrument_code)

        cost_in_instr_ccy = raw_cost_data.calculate_cost_instrument_currency(1.0, multiplier, last_price)
        cost_in_base_ccy = fx_rate * cost_in_instr_ccy

        return cost_in_base_ccy

    def get_final_price(self, instrument_code: str) -> float:
        return self.get_raw_price(instrument_code).ffill().iloc[-1]

    def get_last_fx_rate(self, instrument_code: str) -> float:
        return self.get_fx_rate(instrument_code).ffill().iloc[-1]



    ## INPUTS FROM OTHER STAGES
    def get_implied_expected_returns(self,
                                     relevant_date: datetime.datetime = arg_not_supplied) \
            -> meanEstimates:

        return self.expected_returns_stage.get_implied_expected_returns(relevant_date)

    def get_covariance_matrix(self,
                              relevant_date: datetime.datetime = arg_not_supplied) -> covarianceEstimate:

            return self.expected_returns_stage.get_covariance_matrix(relevant_date=relevant_date)

    def risk_aversion_coefficient(self) -> float:

        return self.expected_returns_stage.risk_aversion_coefficient()

    def annualised_percentage_vol(self, instrument_code: str) -> pd.Series:
        return self.expected_returns_stage.annualised_percentage_vol(instrument_code)

    def get_per_contract_value(self, relevant_date: datetime.datetime = arg_not_supplied):
        return self.expected_returns_stage.get_per_contract_value(relevant_date)

    def get_per_contract_value_as_proportion_of_capital_df(self) -> pd.DataFrame:
        return self.expected_returns_stage.get_per_contract_value_as_proportion_of_capital_df()

    def get_ratio_of_max_to_average_forecast(self) -> float:
        average_forecast = self.forecast_scaling_stage.target_abs_forecast()
        max_forecast = self.forecast_scaling_stage.get_forecast_cap()

        return max_forecast / average_forecast

    def percentage_vol_target(self) -> float:
        return self.position_size_stage.get_percentage_vol_target()

    def instrument_list(self) -> list:
        return self.parent.get_instrument_list()

    def get_instrument_weights(self) -> pd.DataFrame:
        return self.portfolio_stage.get_instrument_weights()

    def common_index(self):
        return self.expected_returns_stage.common_index()

    def original_portfolio_weights_for_relevant_date(self,
                                                     relevant_date: datetime.datetime = arg_not_supplied):
        return self.expected_returns_stage.get_portfolio_weights_for_relevant_date(relevant_date)


    def get_instrument_diversification_multiplier(self) -> pd.Series:
        return self.portfolio_stage.get_instrument_diversification_multiplier()

    def get_raw_cost_data(self, instrument_code: str):
        return self.accounts_stage().get_raw_cost_data(instrument_code)

    def get_contract_multiplier(self, instrument_code: str) -> float:
        return float(self.data.get_value_of_block_price_move(instrument_code))

    def get_raw_price(self, instrument_code: str) -> pd.Series:
        return self.data.get_raw_price(instrument_code)

    def get_fx_rate(self, instrument_code: str) -> pd.Series:
        return self.position_size_stage.get_fx_rate(instrument_code)

    def get_trading_capital(self) -> float:
        return self.position_size_stage.get_notional_trading_capital()

    ## STAGE POINTERS
    def accounts_stage(self):
        return self.parent.accounts

    @property
    def expected_returns_stage(self) -> expectedReturnsStage:
        return self.parent.expectedReturns

    @property
    def position_size_stage(self):
        return self.parent.positionSize

    @property
    def portfolio_stage(self):
        return self.parent.portfolio

    @property
    def forecast_scaling_stage(self):
        return self.parent.forecastScaleCap

    @property
    def data(self):
        return self.parent.data

    @property
    def config(self):
        return self.parent.config

    ## CODE FOR TESTING ONLY NOT USED IN PRODUCTION
    def get_optimal_position_in_contract_units_using_continous_weights(self,
                             relevant_date: datetime.datetime = arg_not_supplied
                                                                       ) -> portfolioWeights:
        ## test to make sure code works and for comparisions
        optimal_weights = self.get_optimal_weights_maximise_with_contionous_weights(relevant_date)
        per_contract_value = self.get_per_contract_value(relevant_date)

        contract_positions = calculate_contract_positions_from_weights_and_values(optimal_weights, per_contract_value)

        return contract_positions

    ## CODE FOR TESTING ONLY NOT USED IN PRODUCTION
    def get_optimal_weights_maximise_with_contionous_weights(self,
                                         relevant_date: datetime.datetime = arg_not_supplied):
        ## test to make sure code works
        covariance_matrix = self.get_covariance_matrix(relevant_date=relevant_date)
        expected_returns = self.get_implied_expected_returns(relevant_date)
        risk_aversion = self.risk_aversion_coefficient()

        optimal_weights = maximise_without_discrete_weights(expected_returns = expected_returns,
                                                        covariance_matrix = covariance_matrix,
                                                            risk_aversion = risk_aversion)

        return optimal_weights



def calculate_contract_positions_from_weights_and_values(optimal_weights: portfolioWeights,
                                                         per_contract_value: portfolioWeights) -> portfolioWeights:

    instrument_list = list(optimal_weights.keys())
    optimal_weights_as_np = np.array(optimal_weights.as_list_given_keys(instrument_list))
    per_contract_value_as_np = np.array(per_contract_value.as_list_given_keys(instrument_list))

    positions_as_np = optimal_weights_as_np / per_contract_value_as_np

    positions = portfolioWeights.from_weights_and_keys(positions_as_np,
                                                       instrument_list)

    return positions


def calculate_max_risk_per_instrument(
                                      idm: pd.Series,
                                      max_instrument_weight: pd.Series,
                                        my_config: dict,
                                        ratio_of_max_to_average_forecast: float = 2.0,
                                    ):
    risk_shifting_multiplier = my_config['risk_shifting_multiplier']  # to allow risk to shift between instruments
    max_risk_per_instrument_for_large_instrument_count = my_config['max_risk_per_instrument_for_large_instrument_count']

    idm_aligned = idm.reindex(max_instrument_weight.index, method="ffill")

    max_risk_per_instrument_for_large_instrument_count = \
        _calculate_max_risk_per_instrument_for_large_instrument_count(idm_aligned=idm_aligned,
                                                                      ratio_of_max_to_average_forecast=ratio_of_max_to_average_forecast,
                                                                      max_risk_per_instrument_for_large_instrument_count=max_risk_per_instrument_for_large_instrument_count
                                                                      )
    max_risk_per_instrument_normal = _calculate_max_risk_per_instrument_normal(
        idm_aligned=idm_aligned,
        max_instrument_weight=max_instrument_weight,
        ratio_of_max_to_average_forecast=ratio_of_max_to_average_forecast,
        risk_shifting_multiplier=risk_shifting_multiplier
    )

    two_series_to_check = \
        pd.concat([max_risk_per_instrument_for_large_instrument_count,
                   max_risk_per_instrument_normal], axis=1)

    max_risk_per_instrument = two_series_to_check.max(axis=1)

    return max_risk_per_instrument

def _calculate_max_risk_per_instrument_normal(
                                      idm_aligned: pd.Series,
                                      max_instrument_weight: pd.Series,
                                        ratio_of_max_to_average_forecast: float = 2.0,
                                      risk_shifting_multiplier: float = 2.0) -> pd.Series:

    max_risk_per_instrument_normal = \
      idm_aligned * max_instrument_weight * ratio_of_max_to_average_forecast * risk_shifting_multiplier

    return max_risk_per_instrument_normal

def _calculate_max_risk_per_instrument_for_large_instrument_count(
                                      idm_aligned: pd.Series,
                                    ratio_of_max_to_average_forecast: float = 2.0,
                                      max_risk_per_instrument_for_large_instrument_count: float = 0.1) -> pd.Series:

    max_risk_per_instrument_for_large_instrument_count_given_forecast = \
        max_risk_per_instrument_for_large_instrument_count * ratio_of_max_to_average_forecast

    max_risk_per_instrument_for_large_instrument_count = \
        pd.Series(max_risk_per_instrument_for_large_instrument_count_given_forecast,
                  index=idm_aligned.index)

    return max_risk_per_instrument_for_large_instrument_count