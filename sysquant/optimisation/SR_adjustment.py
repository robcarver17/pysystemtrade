import scipy.stats as stats
import pandas as pd
import numpy as np

from sysquant.estimators.correlations import boring_corr_matrix_values
from sysquant.optimisation.shared import (
    sigma_from_corr_and_std,
    optimise_from_sigma_and_mean_list,
)


def adjust_dataframe_of_weights_for_SR_costs(
    weights: pd.DataFrame, costs_dict: dict
) -> pd.DataFrame:

    asset_names = list(weights.columns)
    SR_list = [costs_dict[asset] for asset in asset_names]

    # doesn't really matter but we need a figure
    PSEUDO_CORRELATION_FOR_COSTS = 0.5

    # very high as costs are 'certain'
    ASSUMED_LENGTH_OF_DATA_IN_YEARS_FOR_COSTS = 100

    adj_weights = adjust_dataframe_of_weights_for_SR(
        weights,
        SR_list=SR_list,
        years_of_data=ASSUMED_LENGTH_OF_DATA_IN_YEARS_FOR_COSTS,
        avg_correlation=PSEUDO_CORRELATION_FOR_COSTS,
    )

    return adj_weights


def adjust_dataframe_of_weights_for_SR(
    weights: pd.DataFrame,
    SR_list: list,
    avg_correlation: float = 0.5,
    years_of_data: float = 10,
) -> pd.DataFrame:

    list_of_weight_lists = [
        list(weights.iloc[idx].values) for idx in range(len(weights.index))
    ]

    adj_weight_list = adjust_list_of_weight_lists_for_SR(
        list_of_weight_lists,
        SR_list=SR_list,
        avg_correlation=avg_correlation,
        years_of_data=years_of_data,
    )

    adj_weights = pd.DataFrame(
        adj_weight_list, columns=weights.columns, index=weights.index
    )

    return adj_weights


def adjust_list_of_weight_lists_for_SR(
    list_of_weight_lists: list,
    SR_list: list,
    avg_correlation: float = 0.5,
    years_of_data: float = 10,
) -> list:

    adj_weight_list = [
        adjust_weights_for_SR(
            weights_as_list,
            SR_list=SR_list,
            avg_correlation=avg_correlation,
            years_of_data=years_of_data,
        )
        for weights_as_list in list_of_weight_lists
    ]

    return adj_weight_list


def adjust_weights_for_SR(
    weights_as_list: list, SR_list: list, avg_correlation: float, years_of_data: float
) -> list:

    if len(weights_as_list) == 1:
        return weights_as_list

    avg_SR = np.nanmean(SR_list)
    relative_SR_list = [SR - avg_SR for SR in SR_list]
    multipliers = [
        float(multiplier_from_relative_SR(relative_SR, avg_correlation, years_of_data))
        for relative_SR in relative_SR_list
    ]

    new_weights = list(np.array(weights_as_list) * np.array(multipliers))
    norm_new_weights = norm_weights(new_weights)

    return norm_new_weights


def multiplier_from_relative_SR(
    relative_SR: float, avg_correlation: float, years_of_data: float
) -> float:
    # Return a multiplier
    # 1 implies no adjustment required
    ratio = mini_bootstrap_ratio_given_SR_diff(
        relative_SR, avg_correlation, years_of_data
    )

    return ratio


def mini_bootstrap_ratio_given_SR_diff(
    SR_diff: float,
    avg_correlation: float,
    years_of_data: float,
    avg_SR=0.5,
    std=0.15,
    how_many_assets=2,
    p_step=0.2,
):
    """
    Do a parametric bootstrap of portfolio weights to tell you what the ratio should be between an asset which
       has a higher backtested SR (by SR_diff) versus another asset(s) with average Sharpe Ratio (avg_SR)

    All assets are assumed to have same standard deviation and correlation

    :param SR_diff: Difference in performance in Sharpe Ratio (SR) units between one asset and the rest
    :param avg_correlation: Average correlation across portfolio
    :param years_of_data: How many years of data do you have (can be float for partial years)
    :param avg_SR: Should be realistic for your type of trading
    :param std: Standard deviation (doesn't affect results, just a scaling parameter)
    :param how_many_assets: How many assets in the imaginary portfolio
    :param p_step: Step size to go through in the CDF of the mean estimate
    :return: float, ratio of weight of asset with different SR to 1/n weight
    """
    dist_points = np.arange(p_step, stop=(1 - p_step) + 0.00000001, step=p_step)
    list_of_weights = [
        weights_given_SR_diff(
            SR_diff,
            avg_correlation,
            confidence_interval,
            years_of_data,
            avg_SR=avg_SR,
            std=std,
            how_many_assets=how_many_assets,
        )
        for confidence_interval in dist_points
    ]

    array_of_weights = np.array(list_of_weights)
    average_weights = np.nanmean(array_of_weights, axis=0)
    ratio_of_weights = weight_ratio(average_weights)

    if np.sign(ratio_of_weights - 1.0) != np.sign(SR_diff):
        # This shouldn't happen, and only occurs because weight distributions
        # get curtailed at zero
        return 1.0

    return ratio_of_weights


def weight_ratio(weights: list) -> float:
    """
    Return the ratio of weight of first asset to other weights

    :param weights:
    :return: float
    """

    one_over_N_weight = 1.0 / len(weights)
    weight_first_asset = weights[0]

    return weight_first_asset / one_over_N_weight


def weights_given_SR_diff(
    SR_diff: float,
    avg_correlation: float,
    confidence_interval: float,
    years_of_data: float,
    avg_SR=0.5,
    std=0.15,
    how_many_assets=2,
):
    """
    Return the ratio of weight to 1/N weight for an asset with unusual SR

    :param SR_diff: Difference between the SR and the average SR. 0.0 indicates same as average
    :param avg_correlation: Average correlation amongst assets
    :param years_of_data: How long has this been going one
    :param avg_SR: Average SR to use for other asset
    :param confidence_interval: How confident are we about our mean estimate (i.e. cdf point)
    :param how_many_assets: .... are we optimising over (I only consider 2, but let's keep it general)
    :param std: Standard deviation to use

    :return: Ratio of weight, where 1.0 means no difference
    """

    average_mean = avg_SR * std
    asset1_mean = (SR_diff + avg_SR) * std

    mean_difference = asset1_mean - average_mean

    # Work out what the mean is with appropriate confidence
    confident_mean_difference = calculate_confident_mean_difference(
        std, years_of_data, mean_difference, confidence_interval, avg_correlation
    )

    confident_asset1_mean = confident_mean_difference + average_mean

    mean_list = [confident_asset1_mean] + [average_mean] * (how_many_assets - 1)

    weights = optimise_using_correlation(mean_list, avg_correlation, std)

    return list(weights)


def calculate_confident_mean_difference(
    std: float,
    years_of_data: float,
    mean_difference: float,
    confidence_interval: float,
    avg_correlation: float,
) -> float:

    omega_difference = calculate_omega_difference(std, years_of_data, avg_correlation)
    confident_mean_difference = stats.norm(mean_difference, omega_difference).ppf(
        confidence_interval
    )

    return confident_mean_difference


def calculate_omega_difference(
    std: float, years_of_data: float, avg_correlation: float
):

    omega_one_asset = std / (years_of_data) ** 0.5
    omega_variance_difference = 2 * (omega_one_asset**2) * (1 - avg_correlation)
    omega_difference = omega_variance_difference**0.5

    return omega_difference


def optimise_using_correlation(mean_list: list, avg_correlation: float, std: float):
    corr_matrix = boring_corr_matrix_values(len(mean_list), offdiag=avg_correlation)
    stdev_list = np.full(len(mean_list), std)
    sigma = sigma_from_corr_and_std(stdev_list, corr_matrix)

    weights = optimise_from_sigma_and_mean_list(sigma, mean_list)

    return weights


def norm_weights(list_of_weights: list) -> list:
    norm_weights = list(np.array(list_of_weights) / np.sum(list_of_weights))
    return norm_weights
