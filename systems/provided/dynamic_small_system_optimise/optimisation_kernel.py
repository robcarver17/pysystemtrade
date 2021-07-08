import numpy as np
from collections import namedtuple

from syscore.objects import arg_not_supplied
from sysquant.optimisation.shared import variance

SUBOPTIMAL_PORTFOLIO_VALUE = 9999.0

optimisationParameters = namedtuple("optimisationParameters",
                                    ['mus',
                                    'risk_aversion',
                                    'covariance_as_np',
                                    'max_risk_as_variance',
                                    'cost_as_np_in_portfolio_weight_terms',
                                    'previous_weights_as_np'])

gridSearchResults = namedtuple("gridSearchResults", ["value", "weights"])

def neg_return_with_risk_penalty_and_costs(weights: list,
                                           optimisation_parameters: optimisationParameters)\
        -> gridSearchResults:

    weights = np.array(weights)

    risk_aversion = optimisation_parameters.risk_aversion
    covariance_as_np = optimisation_parameters.covariance_as_np
    max_risk_as_variance = optimisation_parameters.max_risk_as_variance

    variance_estimate = float(variance(weights, covariance_as_np))
    if variance_estimate > max_risk_as_variance:
        return gridSearchResults(value = SUBOPTIMAL_PORTFOLIO_VALUE, weights=weights)

    risk_penalty = risk_aversion * variance_estimate /2.0

    mus = optimisation_parameters.mus
    estreturn = float(weights.dot(mus))

    cost_penalty = _calculate_cost_penalty(weights, optimisation_parameters)

    value_to_minimise = -(estreturn - risk_penalty - cost_penalty)
    result = gridSearchResults(value = value_to_minimise,
                               weights=weights)

    return result

def _calculate_cost_penalty(weights: np.array,
                            optimisation_parameters: optimisationParameters):

    cost_as_np_in_portfolio_weight_terms= optimisation_parameters.cost_as_np_in_portfolio_weight_terms
    previous_weights_as_np = optimisation_parameters.previous_weights_as_np

    if previous_weights_as_np is arg_not_supplied:
        cost_penalty = 0.0
    else:
        change_in_weights = weights - previous_weights_as_np
        trade_size = abs(change_in_weights)
        cost_penalty = np.nansum(cost_as_np_in_portfolio_weight_terms * trade_size)

    return cost_penalty