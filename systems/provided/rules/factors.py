import numpy as np

from sysquant.estimators.vol import robust_vol_calc


def factor_trading_rule(demean_factor_value, smooth=90):
    vol = robust_vol_calc(demean_factor_value)
    normalised_factor_value = demean_factor_value / vol
    smoothed_normalised_factor_value = normalised_factor_value.ewm(span=smooth).mean()

    return smoothed_normalised_factor_value


def conditioned_factor_trading_rule(
    demean_factor_value, condition_demean_factor_value, smooth=90
):
    vol = robust_vol_calc(demean_factor_value)
    normalised_factor_value = demean_factor_value / vol

    sign_condition = condition_demean_factor_value.apply(np.sign)
    sign_condition_resample = sign_condition.reindex(
        normalised_factor_value.index
    ).ffill()

    conditioned_factor = normalised_factor_value * sign_condition_resample
    smoothed_conditioned_factor = conditioned_factor.ewm(span=smooth).mean()

    return smoothed_conditioned_factor
