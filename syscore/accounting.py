import pandas as pd
import numpy as np
from scipy.stats import ttest_rel


def account_test(ac1, ac2):
    """
    Given two Account like objects performs a two sided t test of normalised returns

    :param ac1: first set of returns
    :type ac1: accountCurve or pd.DataFrame of returns

    :param ac2: second set of returns
    :type ac2: accountCurve or pd.DataFrame of returns

    :returns: 2 tuple: difference in means, t-test results
    """

    common_ts = sorted(set(list(ac1.index)) & set(list(ac2.index)))

    ac1_common = ac1.cumsum().reindex(common_ts, method="ffill").diff().values
    ac2_common = ac2.cumsum().reindex(common_ts, method="ffill").diff().values

    missing_values = [
        idx
        for idx in range(len(common_ts))
        if (np.isnan(ac1_common[idx]) or np.isnan(ac2_common[idx]))
    ]
    ac1_common = [
        ac1_common[idx] for idx in range(len(common_ts)) if idx not in missing_values
    ]
    ac2_common = [
        ac2_common[idx] for idx in range(len(common_ts)) if idx not in missing_values
    ]

    ac1_common = ac1_common / np.nanstd(ac1_common)
    ac2_common = ac2_common / np.nanstd(ac2_common)

    diff = np.mean(ac1_common) - np.mean(ac2_common)

    return (diff, ttest_rel(ac1_common, ac2_common))
