from sysquant.estimators.estimates import Estimates

from sysquant.optimisation.weights import estimatesWithPortfolioWeights
from sysquant.optimisation.shared import optimise_given_estimates


def shrinkage_optimisation(
    estimates: Estimates,
    shrinkage_SR: float = 0.90,
    shrinkage_corr: float = 0.50,
    ann_target_SR=0.5,
    **weighting_kwargs,
) -> estimatesWithPortfolioWeights:

    estimates = estimates.shrink_correlation_to_average(shrinkage_corr)
    estimates = estimates.shrink_means_to_SR(
        shrinkage_SR=shrinkage_SR, ann_target_SR=ann_target_SR
    )

    estimates_with_portfolio_weights = optimise_given_estimates(
        estimates, **weighting_kwargs
    )

    return estimates_with_portfolio_weights
