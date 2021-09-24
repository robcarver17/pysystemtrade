import datetime
from copy import copy
from dataclasses import dataclass

import numpy as np
import pandas as pd

from syscore.genutils import progressBar, str2Bool, sign
from syscore.objects import arg_not_supplied

from systems.stage import SystemStage
from systems.system_cache import diagnostic

from systems.provided.dynamic_small_system_optimise.portfolio_weights import portfolioWeightsStage

from sysquant.optimisation.weights import portfolioWeights
from sysquant.estimators.covariance import covarianceEstimate
from sysquant.estimators.mean_estimator import meanEstimates


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
        per_contract_value = self.get_per_contract_value(relevant_date)
        original_portfolio_weights = self.original_portfolio_weights_for_relevant_date(relevant_date)

        covariance_matrix = covariance_matrix.clean_correlations()

        costs = self.get_costs_per_contract_as_proportion_of_capital_all_instruments()

        use_process_pool = str2Bool(self.config.small_system['use_process_pool'])

        obj_instance = objectiveFunctionForGreedy(weights_optimal=original_portfolio_weights,
                                                  covariance_matrix=covariance_matrix,
                                                  per_contract_value = per_contract_value,
                                                  weights_prior=previous_weights,
                                                  costs = costs)

        optimal_weights = obj_instance.optimise()

        return optimal_weights



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

    def get_covariance_matrix(self,
                              relevant_date: datetime.datetime = arg_not_supplied) -> covarianceEstimate:

            return self.portfolio_weights_stage.get_covariance_matrix(relevant_date=relevant_date)

    def get_per_contract_value(self, relevant_date: datetime.datetime = arg_not_supplied):
        return self.portfolio_weights_stage.get_per_contract_value(relevant_date)

    def get_per_contract_value_as_proportion_of_capital_df(self) -> pd.DataFrame:
        return self.portfolio_weights_stage.get_per_contract_value_as_proportion_of_capital_df()

    def instrument_list(self) -> list:
        return self.parent.get_instrument_list()

    def get_instrument_weights(self) -> pd.DataFrame:
        return self.portfolio_stage.get_instrument_weights()

    def common_index(self):
        return self.portfolio_weights_stage.common_index()

    def original_portfolio_weights_for_relevant_date(self,
                                                     relevant_date: datetime.datetime = arg_not_supplied):
        return self.portfolio_weights_stage.get_portfolio_weights_for_relevant_date(relevant_date)


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
    def portfolio_weights_stage(self) -> portfolioWeightsStage:
        return self.parent.portfolioWeights

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






@dataclass
class objectiveFunctionForGreedy:
    weights_optimal: portfolioWeights
    covariance_matrix: covarianceEstimate
    per_contract_value: portfolioWeights
    costs: meanEstimates
    trade_shadow_cost: float= 0.1
    weights_prior: portfolioWeights = arg_not_supplied

    def zero_weights_as_np(self):
        count_assets = len(self.keys_with_valid_data)
        weight_start = np.array([0.0] * count_assets)

        return weight_start

    def optimise(self) -> portfolioWeights:
        optimal_weights = self._optimise_for_valid_keys()

        optimal_weights_for_all_keys = \
            optimal_weights.with_zero_weights_for_missing_keys(list(self.weights_optimal.keys()))

        return optimal_weights_for_all_keys

    def _optimise_for_valid_keys(self) -> portfolioWeights:
        weights_without_missing_items_as_np = greedy_algo_across_integer_values(self)
        optimal_weights = \
            portfolioWeights.from_weights_and_keys(
                list_of_keys=self.keys_with_valid_data,
                list_of_weights=list(weights_without_missing_items_as_np))

        return optimal_weights

    def evaluate(self, weights: np.array) -> float:
        solution_gap = weights - self.weights_optimal_as_np
        track_error = \
            (solution_gap.dot(self.covariance_matrix_as_np).dot(solution_gap))**.5

        trade_costs = self.calculate_costs(weights)
        return track_error + trade_costs

    def calculate_costs(self, weights: np.array) -> float:
        if self.no_prior_weights_provided:
            return 0.0
        trade_gap = weights - self.weights_prior_as_np
        costs_per_trade = self.costs_as_np
        trade_costs = sum(abs(costs_per_trade * trade_gap * self.trade_shadow_cost))

        return trade_costs

    @property
    def no_prior_weights_provided(self) -> bool:
        return self.weights_prior is arg_not_supplied

    @property
    def keys_with_valid_data(self) -> list:
        valid_correlation_keys = self.covariance_matrix.assets_with_data()
        valid_optimal_weight_keys = self.weights_optimal.assets_with_data()
        valid_per_contract_keys = self.per_contract_value.assets_with_data()

        valid_correlation_keys_set = set(valid_correlation_keys)
        valid_optimal_weight_keys_set = set(valid_optimal_weight_keys)
        valid_per_contract_keys_set = set(valid_per_contract_keys)

        valid_keys = valid_correlation_keys_set.intersection(valid_optimal_weight_keys_set)
        valid_keys = valid_keys.intersection(valid_per_contract_keys_set)

        return list(valid_keys)

    @property
    def weights_optimal_as_np(self) -> np.array:
        weights_optimal_as_np = getattr(self, "_weights_optimal_as_np", None)
        if weights_optimal_as_np is None:
            weights_optimal_as_np = \
                np.array(
                    self.weights_optimal.as_list_given_keys(
                    self.keys_with_valid_data))
            self._weights_optimal_as_np = weights_optimal_as_np

        return weights_optimal_as_np

    @property
    def per_contract_value_as_np(self) -> np.array:
        per_contract_value_as_np = getattr(self, "_per_contract_value_as_np", None)
        if per_contract_value_as_np is None:
            per_contract_value_as_np = np.array(
                self.per_contract_value.as_list_given_keys(
                    self.keys_with_valid_data
                ))
            self._per_contract_value_as_np = per_contract_value_as_np

        return per_contract_value_as_np

    @property
    def weights_prior_as_np(self) -> np.array:
        weights_prior_as_np = getattr(self, "_weights_prior_as_np", None)
        if weights_prior_as_np is None:
            weights_prior_as_np = np.array(
                self.weights_prior.as_list_given_keys(
                  self.keys_with_valid_data
                ))
            self._weights_prior_as_np = weights_prior_as_np

        return weights_prior_as_np

    @property
    def covariance_matrix_as_np(self) -> np.array:
        covariance_matrix_as_np = getattr(self, "_covariance_matrix_as_np", None)
        if covariance_matrix_as_np is None:
            covariance_matrix_as_np = self.covariance_matrix.subset(
                self.keys_with_valid_data
            ).values
            self._covariance_matrix_as_np  = covariance_matrix_as_np

        return covariance_matrix_as_np

    @property
    def costs_as_np(self) -> np.array:
        costs_as_np = getattr(self, "_costs_as_np", None)
        if costs_as_np is None:
            costs_as_np = np.array(list(self.costs.subset(
                self.keys_with_valid_data
            ).values()))
            self._costs_as_np = costs_as_np

        return costs_as_np

    @property
    def optimal_signs_as_np(self) -> np.array:
        optimal_signs = getattr(self, "_optimal_signs", None)
        if optimal_signs is None:
            optimal_signs = self._calculate_optimal_signs()
            self._optimal_signs = optimal_signs

        return optimal_signs

    def _calculate_optimal_signs(self) -> np.array:
        weights_optimal_as_np = self.weights_optimal_as_np
        optimal_signs = np.array([sign(x) for x in weights_optimal_as_np])

        return optimal_signs




def greedy_algo_across_integer_values(
        obj_instance: objectiveFunctionForGreedy
                                    ) -> np.array:

    weight_start = obj_instance.zero_weights_as_np()
    best_value = obj_instance.evaluate(weight_start)
    best_solution = weight_start

    done = False

    while not done:
        new_best_value, new_solution = find_possible_new_best(best_solution = best_solution,
                                                              best_value=best_value,
                                                              obj_instance=obj_instance)

        if new_best_value<best_value:
            # reached a new optimium
            best_value = new_best_value
            best_solution = new_solution
        else:
            # we can't do any better
            break

    return best_solution

def find_possible_new_best(best_solution: np.array,
                           best_value: float,
                           obj_instance: objectiveFunctionForGreedy) -> tuple:

    new_best_value = best_value
    new_solution = best_solution

    fixed_units = obj_instance.per_contract_value_as_np
    weight_sign = obj_instance.optimal_signs_as_np

    count_assets = len(best_solution)
    for i in range(count_assets):
        temp_step = copy(best_solution)
        temp_step[i] = temp_step[i] + fixed_units[i] * weight_sign[i]
        temp_objective_value = obj_instance.evaluate(temp_step)
        if temp_objective_value < new_best_value:
            new_best_value = temp_objective_value
            new_solution = temp_step

    return new_best_value, new_solution
