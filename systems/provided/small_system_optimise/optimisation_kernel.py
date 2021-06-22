import numpy as np

from syscore.objects import arg_not_supplied
from sysquant.optimisation.shared import variance

SUBOPTIMAL_PORTFOLIO_VALUE = 9999.0

def neg_return_with_risk_penalty_and_costs(weights: list,
                                           optimisation_parameters: tuple):

    mus, risk_aversion, covariance_as_np, max_risk_as_variance, \
        cost_as_np_in_portfolio_weight_terms, previous_weights_as_np = optimisation_parameters

    weights = np.array(weights)

    if previous_weights_as_np is arg_not_supplied:
        cost_penalty = 0.0
    else:
        change_in_weights = weights - previous_weights_as_np
        trade_size = abs(change_in_weights)
        cost_penalty = np.nansum(cost_as_np_in_portfolio_weight_terms * trade_size)

    variance_estimate = float(variance(weights, covariance_as_np))
    if variance_estimate > max_risk_as_variance:
        return SUBOPTIMAL_PORTFOLIO_VALUE

    estreturn = float(weights.dot(mus))

    risk_penalty = risk_aversion * variance_estimate /2.0

    return -(estreturn - risk_penalty - cost_penalty)