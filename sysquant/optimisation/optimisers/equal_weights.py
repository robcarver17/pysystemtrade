from sysquant.optimisation.weights import (
    one_over_n_portfolio_weights_from_estimates,
    estimatesWithPortfolioWeights,
)
from sysquant.estimators.estimates import Estimates


def equal_weights_optimisation(
    estimates: Estimates, **_ignore_weighting_args
) -> estimatesWithPortfolioWeights:

    portfolio_weights = one_over_n_portfolio_weights_from_estimates(estimates)
    estimates_with_weights = estimatesWithPortfolioWeights(
        weights=portfolio_weights, estimates=estimates
    )

    return estimates_with_weights
