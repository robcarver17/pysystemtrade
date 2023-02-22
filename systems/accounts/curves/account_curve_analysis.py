import pandas as pd
from typing import Union, NamedTuple
from scipy.stats import ttest_rel

from systems.accounts.curves.account_curve import accountCurve


class AccountTTestResult(NamedTuple):
    """Structure to store the results of the t-test"""

    diff: float
    statistic: float
    pvalue: float


def account_t_test(
    acc1: Union[accountCurve, pd.Series], acc2: Union[accountCurve, pd.Series]
) -> AccountTTestResult:
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

    standardised_df_returns = _prepare_returns_data_for_t_test(acc1=acc1, acc2=acc2)

    means = standardised_df_returns.mean(axis=0).values
    returns = standardised_df_returns.values

    # Get the difference in (standardised) means
    diff = means[0] - means[1]

    # Perform the two-sided t-test
    ttest_results = ttest_rel(returns[:, 0], returns[:, 1], nan_policy="omit")
    t = ttest_results.statistic
    pvalue = ttest_results.pvalue

    return AccountTTestResult(diff, t, pvalue)


def _prepare_returns_data_for_t_test(
    acc1: Union[accountCurve, pd.Series], acc2: Union[accountCurve, pd.Series]
) -> pd.DataFrame:
    # Inner join on the cumulative returns
    acc1 = pd.DataFrame(acc1).cumsum()
    acc2 = pd.DataFrame(acc2).cumsum()
    cum = pd.merge(acc1, acc2, left_index=True, right_index=True)
    cum = cum.sort_index(ascending=True, inplace=False)

    # Get returns, standardise and compute means
    df_returns = cum.diff(periods=1).dropna(how="any")
    standardised_df_returns = df_returns / (df_returns.std(axis=0) + 1e-100)

    return standardised_df_returns


def standard_statistics(account_curve: accountCurve):
    acc = account_curve.percent
    costs = acc.costs.ann_mean()
    print("Ann Mean %.1f" % acc.ann_mean())
    print("Gross ann mean %.1f" % acc.gross.ann_mean())
    print("costs %.2f" % costs)
    print("drawdown %.1f" % acc.avg_drawdown())
    print("std dev %.1f" % acc.ann_std())
    print("SR %.2f" % acc.sharpe())
    print("turnover %.1f" % system.accounts.total_portfolio_level_turnover())
    print("daily skew %.2f" % acc.daily.skew())
    print("weekly skew %.2f" % acc.weekly.skew())
    print("monthly skew %.2f" % acc.monthly.skew())
    print("annual skew %.2f" % acc.annual.skew())

    print("lpr %.2f" % acc.quant_ratio_lower())
    print("upr %.2f" % acc.quant_ratio_upper())
