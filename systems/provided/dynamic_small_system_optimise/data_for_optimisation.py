from copy import copy
import numpy as np

from syscore.constants import missing_data, arg_not_supplied
from sysquant.optimisation.weights import portfolioWeights
from systems.provided.dynamic_small_system_optimise.set_up_constraints import (
    A_VERY_LARGE_NUMBER,
    calculate_min_max_and_direction_and_start,
)


class dataForOptimisation(object):
    def __init__(self, obj_instance: "objectiveFunctionForGreedy"):
        self.covariance_matrix = obj_instance.covariance_matrix
        self.weights_optimal = obj_instance.weights_optimal
        self.per_contract_value = obj_instance.per_contract_value
        self.costs = obj_instance.costs

        if obj_instance.constraints is arg_not_supplied:
            reduce_only_keys = no_trade_keys = arg_not_supplied

        else:
            no_trade_keys = obj_instance.constraints.no_trade_keys
            reduce_only_keys = obj_instance.constraints.reduce_only_keys

        self.no_trade_keys = no_trade_keys
        self.reduce_only_keys = reduce_only_keys

        self.weights_prior = obj_instance.weights_prior
        self.maximum_position_weights = obj_instance.maximum_position_weights

    def get_key(self, keyname):
        reference = "_stored_" + keyname
        stored_value = getattr(self, reference, missing_data)
        if stored_value is missing_data:
            calculated_value = getattr(self, "_" + keyname)
            setattr(self, reference, calculated_value)
            return calculated_value
        else:
            return stored_value

    def set_key(self, keyname, value):
        reference = "_stored_" + keyname
        setattr(self, reference, value)

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

    @covariance_matrix_as_np.setter
    def covariance_matrix_as_np(self, cov_matrix: np.array):
        self.set_key("covariance_matrix_as_np", cov_matrix)

    @property
    def costs_as_np(self) -> np.array:
        return self.get_key("costs_as_np")

    @property
    def weights_prior_as_np_replace_nans_with_zeros(self) -> np.array:
        return self.get_key("weights_prior_as_np_replace_nans_with_zeros")

    @property
    def starting_weights_as_np(self) -> np.array:
        return self.get_key("starting_weights_as_np")

    @property
    def direction_as_np(self) -> np.array:
        return self.get_key("direction_as_np")

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
        weights_optimal_as_np = np.array(
            self.weights_optimal.as_list_given_keys(self.keys_with_valid_data)
        )

        return weights_optimal_as_np

    @property
    def _per_contract_value_as_np(self) -> np.array:
        per_contract_value_as_np = np.array(
            self.per_contract_value.as_list_given_keys(self.keys_with_valid_data)
        )

        return per_contract_value_as_np

    @property
    def _weights_prior_as_np_replace_nans_with_zeros(self) -> np.array:
        weights_prior_as_np = copy(self.weights_prior_as_np)

        if self.weights_prior_as_np is arg_not_supplied:
            return arg_not_supplied

        def _zero_if_nan(x):
            if np.isnan(x):
                return 0
            else:
                return x

        weights_prior_as_np_zero_replaced = [
            _zero_if_nan(x) for x in weights_prior_as_np
        ]

        return np.array(weights_prior_as_np_zero_replaced)

    @property
    def _weights_prior_as_np(self) -> np.array:
        if self.weights_prior is arg_not_supplied:
            return arg_not_supplied

        weights_prior_as_np = np.array(
            self.weights_prior.as_list_given_keys(self.keys_with_valid_data)
        )

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
        costs_as_np = np.array(list(costs.subset(self.keys_with_valid_data).values()))

        return costs_as_np

    @property
    def _starting_weights_as_np(self) -> np.array:
        starting_weights = self._starting_weights
        starting_weights_as_np = np.array(
            list(starting_weights.as_list_given_keys(self.keys_with_valid_data))
        )

        return starting_weights_as_np

    @property
    def _direction_as_np(self) -> np.array:
        direction = self._direction
        direction_as_np = np.array(
            list(direction.as_list_given_keys(self.keys_with_valid_data))
        )

        return direction_as_np

    ## not cached as only called at init of data
    def optimal_weights_for_code(self, instrument_code: str) -> float:
        optimal_weights = self.weights_optimal
        return optimal_weights.get(instrument_code, np.nan)

    def maximum_position_weight_for_code(self, instrument_code: str) -> float:
        maximum_position_weights = self.maximum_position_weights
        if maximum_position_weights is arg_not_supplied:
            return A_VERY_LARGE_NUMBER
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
        return self._min_max_and_direction_start.minima

    @property
    def _maxima(self) -> portfolioWeights:
        return self._min_max_and_direction_start.maxima

    @property
    def _starting_weights(self) -> portfolioWeights:
        return self._min_max_and_direction_start.starting_weights

    @property
    def _direction(self) -> portfolioWeights:
        return self._min_max_and_direction_start.direction

    @property
    def _min_max_and_direction_start(self) -> "minMaxAndDirectionAndStart":
        min_max_and_direction_start = calculate_min_max_and_direction_and_start(self)

        return min_max_and_direction_start

    @property
    def _keys_with_valid_data(self) -> list:
        valid_correlation_keys = self.covariance_matrix.assets_with_data()
        valid_optimal_weight_keys = self.weights_optimal.assets_with_data()
        valid_per_contract_keys = self.per_contract_value.assets_with_data()

        valid_correlation_keys_set = set(valid_correlation_keys)
        valid_optimal_weight_keys_set = set(valid_optimal_weight_keys)
        valid_per_contract_keys_set = set(valid_per_contract_keys)

        valid_keys = valid_correlation_keys_set.intersection(
            valid_optimal_weight_keys_set
        )
        valid_keys = valid_keys.intersection(valid_per_contract_keys_set)

        return list(valid_keys)
