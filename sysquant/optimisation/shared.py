import numpy as np

FLAG_BAD_RETURN = -9999999.9
FLAG_BAD_SIGMA = 999999

from scipy.optimize import minimize

from sysquant.optimisation.weights import (
    portfolioWeights,
    estimatesWithPortfolioWeights,
)
from sysquant.estimators.estimates import Estimates


def optimise_given_estimates(
    estimates: Estimates,
    equalise_SR: bool = True,
    ann_target_SR: float = 0.5,
    equalise_vols: bool = True,
    **_ignored_kwargs,
) -> estimatesWithPortfolioWeights:

    estimates = estimates.equalise_estimates(
        equalise_vols=equalise_vols,
        equalise_SR=equalise_SR,
        ann_target_SR=ann_target_SR,
    )

    portfolio_weights = optimise_from_processed_estimates(estimates)
    estimates_with_portfolio_weights = estimatesWithPortfolioWeights(
        weights=portfolio_weights, estimates=estimates
    )

    return estimates_with_portfolio_weights


def optimise_from_processed_estimates(estimates: Estimates) -> portfolioWeights:
    stdev_list = estimates.stdev_list
    corrmatrix = estimates.correlation_matrix
    mean_list = estimates.mean_list
    list_of_asset_names = estimates.asset_names

    sigma = sigma_from_corr_and_std(stdev_list=stdev_list, corrmatrix=corrmatrix)

    weights = optimise_from_sigma_and_mean_list(sigma, mean_list=mean_list)

    portfolio_weights = portfolioWeights.from_weights_and_keys(
        list_of_weights=weights, list_of_keys=list_of_asset_names
    )

    return portfolio_weights


def sigma_from_corr_and_std(stdev_list: list, corrmatrix: list):
    sigma = np.diag(stdev_list).dot(corrmatrix).dot(np.diag(stdev_list))
    return sigma


def optimise_from_sigma_and_mean_list(sigma: np.array, mean_list: list) -> list:

    mus = np.array(mean_list, ndmin=2).transpose()
    number_assets = sigma.shape[1]
    start_weights = [1.0 / number_assets] * number_assets

    # Constraints - positive weights, adding to 1.0
    bounds = [(0.0, 1.0)] * number_assets
    cdict = [{"type": "eq", "fun": addem}]
    ans = minimize(
        neg_SR,
        start_weights,
        (sigma, mus),
        method="SLSQP",
        bounds=bounds,
        constraints=cdict,
        tol=0.00001,
    )

    # anything that had a nan will now have a zero weight
    weights = ans["x"]

    return weights


def fix_mus(mean_list):
    """
    Replace nans with unfeasibly large negatives

    result will be zero weights for these assets
    """

    return fix_vector(mean_list, replace_with=FLAG_BAD_RETURN)


def fix_stdev(stdev_list):
    """
    Replace nans with unfeasibly large

    result will be zero weights for these assets
    """

    return fix_vector(stdev_list, replace_with=FLAG_BAD_SIGMA)


def fix_vector(vector_list, replace_with=FLAG_BAD_RETURN):
    """
    Replace nans with unfeasibly large negatives

    result will be zero weights for these assets
    """

    def _fixit(x):
        if np.isnan(x):
            return replace_with
        else:
            return x

    new_list = [_fixit(x) for x in vector_list]

    return new_list


def un_fix_weights(mean_list, weights):
    """
    When mean has been replaced, use nan weight
    """

    def _unfixit(xmean, xweight):
        if xmean == FLAG_BAD_RETURN:
            return np.nan
        else:
            return xweight

    fixed_weights = [
        _unfixit(xmean, xweight) for (xmean, xweight) in zip(mean_list, weights)
    ]

    return fixed_weights


def fix_sigma(sigma):
    """
    Replace nans with very large numbers

    """

    return fix_matrix(sigma, replace_with=FLAG_BAD_SIGMA)


def fix_correlation(sigma):
    """
    Replace nans with very large numbers

    """

    return fix_matrix(sigma, replace_with=FLAG_BAD_SIGMA)


def fix_matrix(some_matrix, replace_with=FLAG_BAD_SIGMA):
    """
    Replace nans with very large numbers

    """

    def _fixit(x):
        if np.isnan(x):
            return replace_with
        else:
            return x

    new_matrix = [[_fixit(x) for x in sigma_row] for sigma_row in some_matrix]

    new_matrix = np.array(new_matrix)

    return new_matrix


def neg_SR(weights: np.array, sigma: np.array, mus: np.array):
    # Returns minus the Sharpe Ratio (as we're minimising)

    estreturn = float(weights.dot(mus))
    std_dev = variance(weights, sigma) ** 0.5

    return -estreturn / std_dev


def variance(weights: np.matrix, sigma: np.array):
    # returns the variance (NOT standard deviation) given weights and sigma
    return weights.dot(sigma).dot(weights.transpose())


def addem(weights: list):
    # Used for constraints
    return 1.0 - sum(weights)
