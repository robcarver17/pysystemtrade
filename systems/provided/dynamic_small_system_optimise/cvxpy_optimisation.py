from copy import copy
from dataclasses import dataclass

import numpy as np

from syscore.genutils import sign
from syscore.objects import arg_not_supplied, missing_data
from sysquant.estimators.covariance import covarianceEstimate
from sysquant.estimators.mean_estimator import meanEstimates
from sysquant.optimisation.weights import portfolioWeights

default_max_portfolio_weight = 2.0


@dataclass
class objectiveFunctionForMixedInt:
    weights_optimal: portfolioWeights
    covariance_matrix: covarianceEstimate
    per_contract_value: portfolioWeights
    costs: meanEstimates
    trade_shadow_cost: float= 10
    weights_prior: portfolioWeights = arg_not_supplied
    reduce_only_keys: list = arg_not_supplied,
    no_trade_keys: list = arg_not_supplied,
    maximum_position_weights: portfolioWeights = arg_not_supplied


    def evaluate_contracts(self, contracts: np.array):
        weights = self.from_contracts_to_weights(contracts)

        return self.evaluate_weights(weights)

    def from_contracts_to_weights(self, contracts: np.array) -> np.array:
        per_contract_value = self.per_contract_value_as_np
        return per_contract_value * contracts

    def evaluate_weights(self, weights: np.array) -> float:
        solution_gap = weights - self.weights_optimal_as_np
        track_error = \
            (solution_gap.dot(self.covariance_matrix_as_np).dot(solution_gap))**.5

        trade_costs = self.calculate_costs(weights)

        return track_error + trade_costs

    def calculate_costs(self, weights: np.array) -> float:
        trade_gap = weights - self.weights_prior_as_np
        costs_per_trade = self.costs_as_np
        trade_costs = sum(abs(costs_per_trade * trade_gap * self.trade_shadow_cost))

        return trade_costs

    @property
    def no_prior_weights_provided(self) -> bool:
        return self.weights_prior is arg_not_supplied

    @property
    def use_shadow_cost(self) -> float:
        if self.no_prior_weights_provided:
            return 0.0
        else:
            return self.trade_shadow_cost

    @property
    def maxima_as_np(self) -> np.array:
        return self.input_data.maxima_as_np

    @property
    def minima_as_np(self) -> np.array:
        return self.input_data.minima_as_np

    @property
    def keys_with_valid_data(self) -> list:
        return  self.input_data.keys_with_valid_data

    @property
    def weights_optimal_as_np(self) -> np.array:
        return self.input_data.weights_optimal_as_np

    @property
    def per_contract_value_as_np(self) -> np.array:
        return self.input_data.per_contract_value_as_np

    @property
    def weights_prior_as_np(self) -> np.array:
        return self.input_data.weights_prior_as_np

    @property
    def covariance_matrix_as_np(self) -> np.array:
        return self.input_data.covariance_matrix_as_np

    @property
    def costs_as_np(self) -> np.array:
        return self.input_data.costs_as_np

    @property
    def input_data(self):
        input_data = getattr(self, "_input_data", None)
        if input_data is None:
            input_data = dataForOptimisation(self)
            self._input_data = input_data

        return input_data




class dataForOptimisation(object):
    def __init__(self, obj_instance: objectiveFunctionForMixedInt):
        self.covariance_matrix = obj_instance.covariance_matrix
        self.weights_optimal = obj_instance.weights_optimal
        self.per_contract_value = obj_instance.per_contract_value
        self.costs = obj_instance.costs
        self.no_trade_keys = obj_instance.no_trade_keys
        self.weights_prior = obj_instance.weights_prior
        self.reduce_only_keys = obj_instance.reduce_only_keys
        self.maximum_position_weights = obj_instance.maximum_position_weights

    def get_key(self, keyname):
        reference = "_stored_" + keyname
        stored_value = getattr(self, reference, missing_data)
        if stored_value is missing_data:
            calculated_value = getattr(self, "_"+keyname)
            setattr(self, reference, calculated_value)
            return calculated_value
        else:
            return stored_value

    @property
    def weights_optimal_as_np(self) -> list:
        return self.get_key("weights_optimal_as_np")

    @property
    def keys_with_valid_data(self) -> list:
        return self.get_key("keys_with_valid_data")

    @property
    def per_contract_value_as_np(self) -> np.array:
        return self.get_key("per_contract_value_as_np")

    @property
    def weights_prior_as_np(self) -> np.array:
        return self.get_key("weights_prior_as_np")

    @property
    def covariance_matrix_as_np(self) -> np.array:
        return self.get_key("covariance_matrix_as_np")

    @property
    def costs_as_np(self) -> np.array:
        return self.get_key("costs_as_np")

    @property
    def minima_as_np(self) -> np.array:
        return self.get_key("minima_as_np")

    @property
    def maxima_as_np(self) -> np.array:
        return self.get_key("maxima_as_np")

    ## these functions are called first time
    @property
    def _minima_as_np(self) -> np.array:
        minima = self._minima
        minima_as_np = minima.as_list_given_keys(self.keys_with_valid_data)

        return minima_as_np

    @property
    def _maxima_as_np(self) -> np.array:
        maxima = self._maxima
        maxima_as_np = maxima.as_list_given_keys(self.keys_with_valid_data)

        return maxima_as_np

    @property
    def _weights_optimal_as_np(self) -> np.array:
        weights_optimal_as_np = \
            np.array(
                self.weights_optimal.as_list_given_keys(
                self.keys_with_valid_data))

        return weights_optimal_as_np

    @property
    def _per_contract_value_as_np(self) -> np.array:
        per_contract_value_as_np = np.array(
            self.per_contract_value.as_list_given_keys(
                self.keys_with_valid_data
            ))

        return per_contract_value_as_np

    @property
    def _weights_prior_as_np(self) -> np.array:
        if self.weights_prior is arg_not_supplied:
            return arg_not_supplied

        weights_prior_as_np = np.array(
            self.weights_prior.as_list_given_keys(
              self.keys_with_valid_data
            ))

        return weights_prior_as_np

    @property
    def _covariance_matrix_as_np(self) -> np.array:
        covariance_matrix_as_np = self.covariance_matrix.subset(
            self.keys_with_valid_data
        ).values

        return covariance_matrix_as_np

    @property
    def _costs_as_np(self) -> np.array:
        costs = self.costs
        costs_as_np = np.array(list(costs.subset(
            self.keys_with_valid_data
        ).values()))

        return costs_as_np


    ## not cached as only called at init of data
    def optimal_weights_for_code(self, instrument_code: str) -> float:
        optimal_weights = self.weights_optimal
        return optimal_weights.get(instrument_code, np.nan)

    def maximum_position_weight_for_code(self, instrument_code: str) -> float:
        maximum_position_weights = self.maximum_position_weights
        if maximum_position_weights is arg_not_supplied:
            return default_max_portfolio_weight
        else:
            return maximum_position_weights.get(instrument_code, arg_not_supplied)

    def prior_weight_for_code(self, instrument_code: str) -> float:
        prior_weights = self.weights_prior
        if prior_weights is arg_not_supplied:
            return arg_not_supplied
        else:
            return prior_weights.get(instrument_code, arg_not_supplied)

    def per_contract_value_for_code(self, instrument_code: str) -> float:
        per_contract_value = self.per_contract_value
        return per_contract_value.get(instrument_code, np.isnan)

    ## not cached as not used by outside functions
    @property
    def _minima(self) -> portfolioWeights:
        return self._min_max_object.minima

    @property
    def _maxima(self) -> portfolioWeights:
        return self._min_max_object.maxima

    @property
    def _min_max_object(self):
        min_max_object = calculate_min_and_max(self)

        return min_max_object


    @property
    def _keys_with_valid_data(self) -> list:
        valid_correlation_keys = self.covariance_matrix.assets_with_data()
        valid_optimal_weight_keys = self.weights_optimal.assets_with_data()
        valid_per_contract_keys = self.per_contract_value.assets_with_data()

        valid_correlation_keys_set = set(valid_correlation_keys)
        valid_optimal_weight_keys_set = set(valid_optimal_weight_keys)
        valid_per_contract_keys_set = set(valid_per_contract_keys)

        valid_keys = valid_correlation_keys_set.intersection(valid_optimal_weight_keys_set)
        valid_keys = valid_keys.intersection(valid_per_contract_keys_set)

        return list(valid_keys)






class allMinAndMax(dict):
    @property
    def minima(self) -> portfolioWeights:
        return portfolioWeights(self._get_dict_for_value_across_codes('minimum'))

    @property
    def maxima(self) -> portfolioWeights:
        return portfolioWeights(self._get_dict_for_value_across_codes('maximum'))

    def _get_dict_for_value_across_codes(self, entry_name: str):

        return dict([(instrument_code, getattr(dict_value, entry_name))
                     for instrument_code, dict_value in self.items()])


@dataclass
class minAndMaxForCode:
    minimum: float
    maximum: float


def calculate_min_and_max(input_data: dataForOptimisation) -> allMinAndMax:
    all_codes = list(input_data.weights_optimal.keys())
    all_results = dict([(instrument_code,
                         get_data_and_calculate_for_code(instrument_code,
                                                         input_data=input_data))
                        for instrument_code in all_codes])

    return allMinAndMax(all_results)

def get_data_and_calculate_for_code(instrument_code: str,
                                    input_data: dataForOptimisation) \
        -> minAndMaxForCode:

    if input_data.reduce_only_keys is arg_not_supplied:
        reduce_only = False
    else:
        reduce_only = instrument_code in input_data.reduce_only_keys

    if input_data.no_trade_keys is arg_not_supplied:
        no_trade = False
    else:
        no_trade = instrument_code in input_data.no_trade_keys

    max_position = input_data.maximum_position_weight_for_code(instrument_code)
    weight_prior = input_data.prior_weight_for_code(instrument_code)
    per_contract_value = input_data.per_contract_value_for_code(instrument_code)

    min_max_for_code = calculations_for_code(
        reduce_only=reduce_only,
        no_trade=no_trade,
        max_position=max_position,
        weight_prior=weight_prior,
        per_contract_value=per_contract_value
    )

    return min_max_for_code


def calculations_for_code(reduce_only: bool = False,
                          no_trade: bool = False,
                          max_position: float = arg_not_supplied,
                          weight_prior: float = arg_not_supplied,
                          per_contract_value: float = np.nan):

    # required because weights vary slightly
    # if it was 0.5 then could get rounding issues
    weight_tolerance = per_contract_value * .25

    minimum_weight, maximum_weight = calculate_minima_and_maxima_weights(reduce_only=reduce_only,
                                                   no_trade=no_trade,
                                                   max_position=max_position,
                                                   weight_prior=weight_prior,
                                                   weight_tolerance=weight_tolerance)

    minimum = np.ceil(minimum_weight / per_contract_value)
    maximum = np.floor(maximum_weight / per_contract_value)

    assert maximum >= minimum


    return minAndMaxForCode(minimum=minimum,
                                             maximum=maximum,
            )


A_VERY_LARGE_NUMBER = 10

def calculate_minima_and_maxima_weights(reduce_only: bool = False,
                                no_trade: bool = False,
                                max_position: float = arg_not_supplied,
                                weight_prior: float = arg_not_supplied,
                                weight_tolerance: float = np.nan) -> tuple:

    minimum = -A_VERY_LARGE_NUMBER
    maximum = A_VERY_LARGE_NUMBER

    if no_trade:
        if weight_prior is not arg_not_supplied:
            return weight_prior, weight_prior

    if reduce_only:
        if weight_prior is not arg_not_supplied:
            if weight_prior > 0:
                minimum = 0.0
                maximum = weight_prior + weight_tolerance
            elif weight_prior < 0:
                minimum = weight_prior - weight_tolerance
                maximum = 0.0

            else:
                ## prior weight equals zero, so no trade
                return (0.0, 0.0)

    if max_position is not arg_not_supplied:
        max_position = abs(max_position) + weight_tolerance

        # Most conservative of existing minima/maximum if any
        minimum = max(-max_position, minimum)
        maximum = min(max_position, maximum)

    return minimum, maximum


import cvxpy as cp

"""
minimise track_error + trade_costs

minimise x vector of contracts:
 (solution_gap.dot(self.covariance_matrix_as_np).dot(solution_gap))**.5 + trade_costs
((weights - self.weights_optimal_as_np).dot(self.covariance_matrix_as_np).dot(weights - self.weights_optimal_as_np))**.5 + trade_costs
((weights - self.weights_optimal_as_np).dot(self.covariance_matrix_as_np).dot(weights - self.weights_optimal_as_np))**.5 + trade_costs

((x * per_contract- optimal).
     dot(covariance).
           dot(x*per_contract - optimal))**.5 
              + sum(abs(costs_per_trade * 
                  (x * per_contract - weights_prior_as_np) * 
                      shadow_cost))



"""

def new_algo_across_integer_values(
        obj_instance: objectiveFunctionForMixedInt
                                    ) -> np.array:


    maxima = obj_instance.maxima_as_np
    minima = obj_instance.minima_as_np
    per_contract = obj_instance.per_contract_value_as_np
    covariance = obj_instance.covariance_matrix_as_np
    optimal = obj_instance.weights_optimal_as_np
    costs_per_trade = obj_instance.costs_as_np
    weights_prior = obj_instance.weights_prior
    shadow_cost = obj_instance.use_shadow_cost

    x = cp.Variable(len(maxima), integer=True)

    obj = cp.Minimize((x @ per_contract@covariance@x @ per_contract))


    obj = cp.Minimize(((x @ per_contract- optimal)@
     covariance@
           (x@per_contract - optimal)))


              + sum(abs(costs_per_trade *
                  (x * per_contract - weights_prior) *
                      shadow_cost)))

    prob = cp.Problem(obj)
    prob.solve()

    constraints = [x + y == 1,
                   x - y >= 1]
    objective = cp.Minimize(obj_instance.evaluate_contracts(x))
prob = cp.Problem(objective)
prob.solve()

obj_instance = objectiveFunctionForMixedInt(
    weights_optimal=original_portfolio_weights,
    covariance_matrix=covariance_matrix,
    per_contract_value=per_contract_value,
    costs=costs,
)
