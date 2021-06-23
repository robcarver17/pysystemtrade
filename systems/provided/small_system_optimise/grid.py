from dataclasses import dataclass


import numpy as np

from sysquant.optimisation.weights import portfolioWeights


@dataclass
class gridParameters:
    list_of_instruments: list
    max_portfolio_weights: portfolioWeights
    original_portfolio_weights: portfolioWeights
    per_contract_value: portfolioWeights

    @property
    def original_portfolio_weights_as_list(self) -> list:
        return self.original_portfolio_weights.as_list_given_keys(self.list_of_instruments)

    @property
    def per_contract_value_as_list(self) -> list:
        return self.per_contract_value.as_list_given_keys(self.list_of_instruments)

    @property
    def max_portfolio_weights_as_list(self) -> list:
        return self.max_portfolio_weights.as_list_given_keys(self.list_of_instruments)


## FIX ME TO DO
## add other constraints
## reduce only (needs existing position): conflict with sign change so generate first?
## don't trade (needs existing position)

def generate_grid(grid_parameters: gridParameters):

    constraints = _generate_constraints(grid_parameters)

    grid_points = _generate_grid_given_constraints_and_parameters(constraints = constraints,
                                                             grid_parameters = grid_parameters)

    return grid_points


A_REALLY_BIG_NUMBER = 99999999.0
A_REALLY_BIG_NEGATIVE = -A_REALLY_BIG_NUMBER


def _generate_constraints(grid_parameters: gridParameters) -> list:

    original_weight_constraints = _constraints_from_original_weights(grid_parameters.original_portfolio_weights_as_list)
    max_weight_constraints = _max_weight_constraints(grid_parameters.max_portfolio_weights_as_list)

    collapsed_constraints = _collapse_list_of_constraints_lists([original_weight_constraints,
                                                                 max_weight_constraints])

    return collapsed_constraints


def  _constraints_from_original_weights(original_portfolio_weights_as_list: list):
    constraints = [_constraint_for_original_weight(original_weight)
                   for original_weight in original_portfolio_weights_as_list]
    return constraints


def _constraint_for_original_weight(original_weight):
    ## NEVER CHANGE SIGN FROM ORIGINAL WEIGHT
    if original_weight<0:
        return (A_REALLY_BIG_NEGATIVE, 0.0)
    else:
        return (0.0, A_REALLY_BIG_NUMBER)


def _max_weight_constraints(max_portfolio_weights_as_list: list):
    constraints = [_constraint_for_max_weight_entry(max_weight) for max_weight in max_portfolio_weights_as_list]
    return constraints


def _constraint_for_max_weight_entry(max_weight: float):
    return (-max_weight, max_weight)


def _collapse_list_of_constraints_lists(list_of_constraint_lists):
    """
    >>> _collapse_list_of_constraints_lists([[(-1.0,1.0), (-1.0,0.0)], [(0.0, 2.0), (-1.0, 0.5)]])
    [(0.0,1.0), [-1.0, 0.0])
    """
    ## assumes all same length and in form (min, max)
    size_of_constraints = len(list_of_constraint_lists[0])
    collapsed_constraints = [_collapse_set_of_constraints_given_index(index,
                                                                      list_of_constraint_lists)
    for index in range(size_of_constraints)]

    return collapsed_constraints


def _collapse_set_of_constraints_given_index(index: int,
                                             list_of_constraint_lists:list) -> list:
    list_of_constraints = [entry_in_list[index] for entry_in_list in
                           list_of_constraint_lists]

    collapsed_set = _collapse_set_of_constraints(list_of_constraints)

    return collapsed_set


def _collapse_set_of_constraints(list_of_constraints):
    ## list of tuples (min,max). We return the most conservative
    list_of_mins = [x[0] for x in list_of_constraints]
    list_of_maxes = [x[1] for x in list_of_constraints]

    worst_min = _find_worst_min_constraint(list_of_mins)
    worst_max = _find_worst_max_constraint(list_of_maxes)

    return worst_min, worst_max


def _find_worst_min_constraint(list_of_mins):
    return max(list_of_mins)


def _find_worst_max_constraint(list_of_maxes):
    return min(list_of_maxes)


def _generate_grid_given_constraints_and_parameters(constraints: list,
                                               grid_parameters: gridParameters
                                               ):

    per_contract_value_as_list = grid_parameters.per_contract_value_as_list
    grid_points = [_generate_grid_points_for_instrument(constraints_for_instrument,
                                                        per_contract_value_for_instrument) \
                   for constraints_for_instrument,
                                         per_contract_value_for_instrument
                    in zip(constraints, per_contract_value_as_list)]

    return grid_points


def _generate_grid_points_for_instrument(constraints_for_instrument: tuple,
                                         per_contract_value_for_instrument: float) -> list:

    long_points = _generate_grid_points_for_instrument_long(constraints_for_instrument,
                                                           per_contract_value_for_instrument)
    short_points = _generate_grid_points_for_instrument_short(constraints_for_instrument,
                                                             per_contract_value_for_instrument)

    all_points = np.concatenate([short_points,long_points])

    return list(all_points)


def _generate_grid_points_for_instrument_long(constraints_for_instrument: tuple,
                                         per_contract_value_for_instrument: float) -> np.array:

    min_constraint = constraints_for_instrument[0]
    max_constraint = constraints_for_instrument[1]

    long_points = np.arange(start=0,
                    stop = max_constraint,
                     step = per_contract_value_for_instrument)

    if min_constraint<=0:
        # no need to truncate
        return long_points

    long_points= long_points[long_points>=min_constraint]

    return long_points


def _generate_grid_points_for_instrument_short(constraints_for_instrument: tuple,
                                              per_contract_value_for_instrument: float) -> np.array:
    min_constraint = constraints_for_instrument[0]
    max_constraint = constraints_for_instrument[1]

    short_points = np.arange(start=0,
                            stop=min_constraint,
                            step=-per_contract_value_for_instrument)

    if max_constraint >= 0:
        # no need to truncate
        return short_points

    short_points = short_points[short_points<=max_constraint]

    return short_points