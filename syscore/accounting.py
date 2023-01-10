import pandas as pd
from typing import Union, NamedTuple
from scipy.stats import ttest_rel

from systems.accounts.curves.account_curve import accountCurve


class AccountTestResult(NamedTuple):
    """Structure to store the results of the t-test"""

    diff: float
    statistic: float
    pvalue: float


def account_test(
    acc1: Union[accountCurve, pd.Series], acc2: Union[accountCurve, pd.Series]
) -> AccountTestResult:
    """
    Given two accountCurve-like objects, performs a two-sided t-test on normalised returns.

    Parameters
    ----------
    acc1 : accountCurve or pd.Series
        first set of returns
    acc2 : accountCurve or pd.Series
        second set of returns

    Returns
    -------
    diff : float
        difference in standardised means of returns
    statistic : float
        t-statistic for the t-test
    pvalue : float
        p-value for the t-test
    """

    # Inner join on the cumulative returns
    acc1_ = pd.DataFrame(acc1).cumsum()
    acc2_ = pd.DataFrame(acc2).cumsum()
    cum = pd.merge(acc1_, acc2_, left_index=True, right_index=True)
    cum = cum.sort_index(ascending=True, inplace=False)

    # Get returns, standardise and compute means
    returns = cum.diff(periods=1).dropna(how="any")
    returns = returns / (returns.std(axis=0) + 1e-100)
    means = returns.means(axis=0).values
    returns = returns.values

    # Get the difference in (standardised) means
    diff = means[0] - means[1]

    # Perform the two-sided t-test
    ttest = ttest_rel(returns[:, 0], returns[:, 1], nan_policy="omit")
    t = ttest.statistic
    pvalue = ttest.pvalue

    return AccountTestResult(diff, t, pvalue)
