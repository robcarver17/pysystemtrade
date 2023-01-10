from sysquant.optimisation.optimisers.equal_weights import equal_weights_optimisation
from sysquant.optimisation.optimisers.shrinkage import shrinkage_optimisation
from sysquant.optimisation.optimisers.handcraft import handcraft_optimisation
from sysquant.optimisation.optimisers.one_period import one_period_optimisation

from sysquant.optimisation.weights import (
    estimatesWithPortfolioWeights,
    portfolioWeights,
)
from sysquant.estimators.estimates import Estimates


REGISTER_OF_OPTIMISERS = dict(
    equal_weights=equal_weights_optimisation,
    shrinkage=shrinkage_optimisation,
    handcraft=handcraft_optimisation,
    one_period=one_period_optimisation,
)


def optimiser_for_method(
    method: str, estimates: Estimates, **weighting_args
) -> estimatesWithPortfolioWeights:

    assets_with_missing_data = estimates.assets_with_missing_data()
    estimates_with_only_valid_data = estimates.subset_with_available_data()
    if estimates_with_only_valid_data.size == 0:
        return weights_and_estimates_with_no_valid_data(estimates)

    weights_with_estimates_for_valid_data = call_optimiser(
        method,
        estimates_with_only_valid_data=estimates_with_only_valid_data,
        **weighting_args,
    )

    weights_for_valid_data = weights_with_estimates_for_valid_data.weights

    # nans will be cleaned or zeroed
    weights_for_missing_data = portfolioWeights.allnan(assets_with_missing_data)

    weights = portfolioWeights.from_list_of_subportfolios(
        [weights_for_valid_data, weights_for_missing_data]
    )

    weights_with_estimates_for_valid_data.weights = weights

    return weights_with_estimates_for_valid_data


def weights_and_estimates_with_no_valid_data(
    estimates: Estimates,
) -> estimatesWithPortfolioWeights:
    weights_with_no_valid_data = portfolioWeights.allnan([])
    weights_with_estimates_for_valid_data = estimatesWithPortfolioWeights(
        weights=weights_with_no_valid_data, estimates=estimates
    )

    return weights_with_estimates_for_valid_data


def call_optimiser(
    method: str, estimates_with_only_valid_data: Estimates, **weighting_args
) -> estimatesWithPortfolioWeights:

    optimisation_function = REGISTER_OF_OPTIMISERS.get(method, None)
    if optimisation_function is None:
        error_msg = "Optimiser %s not recognised" % method
        raise Exception(error_msg)

    weights_with_estimates_for_valid_data = optimisation_function(
        estimates_with_only_valid_data, **weighting_args
    )

    return weights_with_estimates_for_valid_data
