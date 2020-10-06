import numpy as np

FLAG_BAD_RETURN = -9999999.9
TARGET_ANN_SR = 0.5

from scipy.optimize import minimize


def clean_weights(weights, must_haves=None, fraction=0.5):
    """
    Make's sure we *always* have some weights where they are needed, by replacing nans
    Allocates fraction of pro-rata weight equally

    :param weights: The weights to clean
    :type weights: list of float

    :param must_haves: The indices of things we must have weights for
    :type must_haves: list of bool

    :param fraction: The amount to reduce missing instrument weights by
    :type fraction: float

    :returns: list of float

    >>> clean_weights([1.0, np.nan, np.nan],   fraction=1.0)
    [0.33333333333333337, 0.33333333333333331, 0.33333333333333331]
    >>> clean_weights([0.4, 0.6, np.nan],  fraction=1.0)
    [0.26666666666666672, 0.40000000000000002, 0.33333333333333331]
    >>> clean_weights([0.4, 0.6, np.nan],  fraction=0.5)
    [0.33333333333333337, 0.5, 0.16666666666666666]
    >>> clean_weights([np.nan, np.nan, 1.0],  must_haves=[False,True,True], fraction=1.0)
    [0.0, 0.5, 0.5]
    >>> clean_weights([np.nan, np.nan, np.nan],  must_haves=[False,False,True], fraction=1.0)
    [0.0, 0.0, 1.0]
    >>> clean_weights([np.nan, np.nan, np.nan],  must_haves=[False,False,False], fraction=1.0)
    [0.0, 0.0, 0.0]
    """
    ###

    if must_haves is None:
        must_haves = [True] * len(weights)

    if not any(must_haves):
        return [0.0] * len(weights)

    needs_replacing = [(np.isnan(x) or x == 0.0) and must_haves[i]
                       for (i, x) in enumerate(weights)]
    keep_empty = [(np.isnan(x) or x == 0.0) and not must_haves[i]
                  for (i, x) in enumerate(weights)]
    no_replacement_needed = [
        (not keep_empty[i]) and (not needs_replacing[i])
        for (i, x) in enumerate(weights)
    ]

    if not any(needs_replacing):
        return weights

    missing_weights = sum(needs_replacing)

    total_for_missing_weights = (fraction *
                                 missing_weights /
                                 (float(np.nansum(no_replacement_needed) +
                                        np.nansum(missing_weights))))

    adjustment_on_rest = 1.0 - total_for_missing_weights

    each_missing_weight = total_for_missing_weights / missing_weights

    def _good_weight(
            value,
            idx,
            needs_replacing,
            keep_empty,
            each_missing_weight,
            adjustment_on_rest):

        if needs_replacing[idx]:
            return each_missing_weight
        if keep_empty[idx]:
            return 0.0
        else:
            return value * adjustment_on_rest

    weights = [
        _good_weight(
            value,
            idx,
            needs_replacing,
            keep_empty,
            each_missing_weight,
            adjustment_on_rest,
        )
        for (idx, value) in enumerate(weights)
    ]

    # This process will screw up weights - let's fix them
    xsum = sum(weights)
    weights = [x / xsum for x in weights]

    return weights


def vol_equaliser(mean_list, stdev_list):
    """
    Normalises returns so they have the in sample vol

    >>> vol_equaliser([1.,2.],[2.,4.])
    ([1.5, 1.5], [3.0, 3.0])
    >>> vol_equaliser([1.,2.],[np.nan, np.nan])
    ([nan, nan], [nan, nan])
    """
    if np.all(np.isnan(stdev_list)):
        return ([np.nan] * len(mean_list), [np.nan] * len(stdev_list))

    avg_stdev = np.nanmean(stdev_list)

    norm_factor = [asset_stdev / avg_stdev for asset_stdev in stdev_list]

    with np.errstate(invalid="ignore"):
        norm_means = [mean_list[i] / norm_factor[i]
                      for (i, notUsed) in enumerate(mean_list)]
        norm_stdev = [stdev_list[i] / norm_factor[i]
                      for (i, notUsed) in enumerate(stdev_list)]

    return (norm_means, norm_stdev)


def SR_equaliser(stdev_list, target_SR):
    """
    Normalises returns so they have the same SR

    >>> SR_equaliser([1., 2.],.5)
    [1.1666666666666665, 1.7499999999999998]
    >>> SR_equaliser([np.nan, 2.],.5)
    [nan, 1.0]
    """
    return [target_SR * asset_stdev for asset_stdev in stdev_list]


def addem(weights):
    # Used for constraints
    return 1.0 - sum(weights)


def variance(weights, sigma):
    # returns the variance (NOT standard deviation) given weights and sigma
    return (weights * sigma * weights.transpose())[0, 0]


def neg_SR(weights, sigma, mus):
    # Returns minus the Sharpe Ratio (as we're minimising)
    weights = np.matrix(weights)
    estreturn = (weights * mus)[0, 0]
    std_dev = variance(weights, sigma) ** 0.5

    return -estreturn / std_dev


def fix_mus(mean_list):
    """
    Replace nans with unfeasibly large negatives

    result will be zero weights for these assets
    """

    def _fixit(x):
        if np.isnan(x):
            return FLAG_BAD_RETURN
        else:
            return x

    mean_list = [_fixit(x) for x in mean_list]

    return mean_list


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
        _unfixit(
            xmean,
            xweight) for (
            xmean,
            xweight) in zip(
                mean_list,
            weights)]

    return fixed_weights


def fix_sigma(sigma):
    """
    Replace nans with zeros

    """

    def _fixit(x):
        if np.isnan(x):
            return 0.0
        else:
            return x

    sigma = [[_fixit(x) for x in sigma_row] for sigma_row in sigma]

    sigma = np.array(sigma)

    return sigma


def optimise(sigma, mean_list):

    # will replace nans with big negatives
    mean_list = fix_mus(mean_list)

    # replaces nans with zeros
    sigma = fix_sigma(sigma)

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

    # put back the nans
    weights = un_fix_weights(mean_list, weights)

    return weights


def sigma_from_corr_and_std(stdev_list, corrmatrix):
    sigma = np.diag(stdev_list).dot(corrmatrix).dot(np.diag(stdev_list))
    return sigma
