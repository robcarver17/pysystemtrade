from syscore.genutils import progressBar
from sysdata.csv.csv_sim_futures_data import csvFuturesSimData
import pandas as pd
import random
from syscore.optimisation import optimise, sigma_from_corr_and_std
import numpy as np
from matplotlib.pyplot import show, legend, hist, subplots, subplot, figure, gca, title
from syscore.correlations import boring_corr_matrix, get_avg_corr
import itertools

# get some returns to play with
# 3 asset problem

data = csvFuturesSimData()


def from_estimate_to_final_value(weekly_mean, weekly_std, years=30):

    returns_to_final_value = [
        random.gauss(weekly_mean, weekly_std) for notUsed in range(years * 52)
    ]
    returns_to_final_value = pd.DataFrame(returns_to_final_value, pd.date_range(
        pd.datetime(2000, 1, 1), periods=len(returns_to_final_value)), )

    return final_value(returns_to_final_value)


def calc_weekly_return(instrument_code, start_date=pd.datetime(1998, 1, 1)):
    price = data[instrument_code]
    price = price[start_date:]
    weekly_price = price.resample("W").last()
    denom_price = data.get_instrument_raw_carry_data(instrument_code).PRICE
    denom_weekly_price = denom_price.resample("W").last()

    weekly_returns = (weekly_price - weekly_price.shift(1)) / \
        denom_weekly_price

    return weekly_returns[1:]


code_list = ["SP500", "US10", "US5"]
corr_pairs = ["SP500/US5", "SP500/US10", "US5/US10"]

returns = dict(
    [
        (instrument_code, calc_weekly_return(instrument_code))
        for instrument_code in code_list
    ]
)
returns = pd.DataFrame(returns)
returns.US5[abs(returns.US5) > 0.04] = np.nan
returns.US10[abs(returns.US10) > 0.04] = np.nan
returns.SP500[abs(returns.SP500) > 0.4] = np.nan

# plot distribution of expected portfolio values
lowrisk = returns.US5
highrisk = returns.SP500

portfolio = returns.SP500 * 0.15 + returns.US5 * 0.5 + returns.US10 * 0.35


def get_sub_sample(returns, bootstrap_length=None):
    if bootstrap_length is None:
        bootstrap_length = len(returns.index)
    bs_idx = [int(random.uniform(0, 1) * len(returns))
              for notUsed in range(bootstrap_length)]

    return returns.iloc[bs_idx, :]


def final_value(some_returns):
    # cumulative returns
    with_one = some_returns + 1.0
    final_value_figure = with_one.product()

    return float(final_value_figure)


def from_estimate_to_final_value(weekly_mean, weekly_std, years=30):
    returns_to_final_value = [
        random.gauss(weekly_mean, weekly_std) for notUsed in range(years * 52)
    ]
    returns_to_final_value = pd.DataFrame(returns_to_final_value, pd.date_range(
        pd.datetime(2000, 1, 1), periods=len(returns_to_final_value)), )
    return final_value(returns_to_final_value)


def distribution_of_final_values_from_estimates(
    weekly_mean, weekly_std, monte_count=100, years=30
):
    bootstrap_list_of_final_values = [
        from_estimate_to_final_value(weekly_mean, weekly_std, years=years)
        for notUsed in range(monte_count)
    ]

    return bootstrap_list_of_final_values


def distribution_of_final_values(
        weekly_returns_to_use,
        monte_count=100,
        years=30):
    weekly_mean = weekly_returns_to_use.mean()
    weekly_std = weekly_returns_to_use.std()
    bootstrap_list_of_final_values = distribution_of_final_values_from_estimates(
        weekly_mean, weekly_std, monte_count, years)

    return bootstrap_list_of_final_values


lowrisk_dist = distribution_of_final_values(lowrisk, monte_count=2500)
subplot(2, 1, 1)
hist(lowrisk_dist, bins=50)

highrisk_dist = distribution_of_final_values(highrisk, monte_count=2500)
subplot(2, 1, 2)
hist(highrisk_dist, bins=50)


def log_the_list(x):
    y = [np.log(xx) for xx in x]
    return y


def median_of_final_portfolio_values_given_estimate(
    weekly_mean, weekly_std, monte_count=100, years=30
):
    final_values = distribution_of_final_values_from_estimates(
        weekly_mean, weekly_std, monte_count, years
    )

    return np.median(final_values)


# now we get the plot including distribution of errors in sampling uncertainty
def distribution_of_estimates(weekly_returns_to_use, monte_count=100):
    weekly_returns_to_use_df = pd.DataFrame(weekly_returns_to_use)
    list_of_sampled_returns = [
        get_sub_sample(
            weekly_returns_to_use_df, bootstrap_length=len(weekly_returns_to_use)
        )
        for notUsed in range(monte_count)
    ]
    mean_estimates = [np.float(sampled_returns.mean())
                      for sampled_returns in list_of_sampled_returns]
    vol_estimates = [np.float(sampled_returns.std())
                     for sampled_returns in list_of_sampled_returns]

    return mean_estimates, vol_estimates


def distr_of_medians(
    weekly_returns_to_use,
    monte_count_estimates=100,
    monte_count_final_value=50,
    years=30,
):

    mean_estimates, vol_estimates = distribution_of_estimates(
        weekly_returns_to_use, monte_count_estimates
    )

    distr_of_median_list = [
        median_of_final_portfolio_values_given_estimate(
            weekly_mean, weekly_std, monte_count=monte_count_final_value, years=years
        )
        for weekly_mean, weekly_std in zip(mean_estimates, vol_estimates)
    ]

    return distr_of_median_list


lowrisk_dist_median = distr_of_medians(lowrisk, monte_count_estimates=2500)
subplot(2, 1, 1)
hist(lowrisk_dist_median, bins=50)

highrisk_dist_median = distr_of_medians(highrisk, monte_count_estimates=2500)
subplot(2, 1, 2)
hist(highrisk_dist_median, bins=500)

# why not empty values
# add black swan event
highrisk[1500] = -0.3

# produce something with same SR and vol as highrisk
portfolio = lowrisk * 0.6 + highrisk * 0.4

portfolio = portfolio * highrisk.std() / portfolio.std()
portfolio = portfolio + highrisk.mean() - portfolio.mean()

highrisk[500]


def distribution_of_final_values_bootstrapped(
    weekly_returns_to_use, monte_count=100, years=30
):
    weekly_returns_to_use_df = pd.DataFrame(weekly_returns_to_use)
    list_of_sampled_returns = [
        get_sub_sample(weekly_returns_to_use_df, bootstrap_length=years * 52)
        for notUsed in range(monte_count)
    ]
    bootstrap_list_of_final_values = [final_value(
        sampled_returns) for sampled_returns in list_of_sampled_returns]

    return bootstrap_list_of_final_values


portfolio_dist = distribution_of_final_values_bootstrapped(
    portfolio, monte_count=10000)
subplot(2, 1, 1)
hist(portfolio_dist, bins=100)

highrisk_dist = distribution_of_final_values_bootstrapped(
    highrisk, monte_count=10000)
subplot(2, 1, 2)
hist(highrisk_dist, bins=200)


def optimisation(
    weekly_returns, equalisecorr=False, equaliseSR=False, riskweights=False
):
    if equalisecorr:
        corrmatrix = np.diag([1.0] * len(returns.columns))
    else:
        corrmatrix = weekly_returns.corr().values
    mean_list = list(annualised_mean(weekly_returns).values)
    stdev_list = list(annualised_std(weekly_returns).values)

    if equaliseSR:
        sr_list = [
            each_return / each_std
            for each_return, each_std in zip(mean_list, stdev_list)
        ]

        avg_sr = np.nanmean(sr_list)
        mean_list = [each_std * avg_sr for each_std in stdev_list]

    if riskweights:
        avg_std = np.nanmean(stdev_list)
        mean_list = [
            this_mean * avg_std / this_std
            for this_mean, this_std in zip(mean_list, stdev_list)
        ]
        stdev_list = [avg_std] * len(stdev_list)

    return optimisation_with_data(corrmatrix, mean_list, stdev_list)


def optimisation_with_data(corrmatrix, mean_list, stdev_list):
    sigma = sigma_from_corr_and_std(stdev_list, corrmatrix)

    weights = optimise(sigma, mean_list)

    return weights


def sharpe_ratio(weekly_returns, funding=0.0):
    return (annualised_mean(weekly_returns) - funding) / \
        annualised_std(weekly_returns)


def optimal_leverage(weekly_returns, funding=0.02):
    SR = (annualised_mean(weekly_returns) - funding) / \
        annualised_std(weekly_returns)
    stdev = annualised_std(weekly_returns)

    return SR / stdev


def annualised_mean(weekly_returns):
    return weekly_returns.mean() * 52.0


def annualised_std(weekly_returns):
    return weekly_returns.std() * (52 ** 0.5)


def corr_as_vector(weekly_returns):
    corr = weekly_returns.corr()
    cvector = [
        corr[code_list[0]][code_list[2]],
        corr[code_list[0]][code_list[1]],
        corr[code_list[1]][code_list[2]],
    ]
    cvector = pd.Series(cvector)
    cvector.index = corr_pairs
    return cvector


# sampling uncertainty of weights ..


def get_bootstrapped_weights(returns, monte_count=100):
    bs_weights = [
        optimisation(get_sub_sample(returns)) for notUsed in range(monte_count)
    ]
    bs_weights = pd.DataFrame(bs_weights)
    bs_weights.columns = returns.columns

    return bs_weights


some_weights = get_bootstrapped_weights(returns, 10000)
bins = 50

hist(some_weights.US10, bins=bins)

# the effect of optimisation inputs on weights
# double graph, bottom shows distribution of relevant statistic
# top shows effect on portfolio


def some_random_bootstrapped_returns(returns, horizon=None):
    if horizon is None:
        horizon = len(returns.index)

    draws = [int(random.uniform(0, len(returns)))
             for notused in range(horizon)]

    return returns.iloc[
        draws,
    ]


def statistic_from_bootstrap(returns, stat_function, horizon=None):

    subset_returns = some_random_bootstrapped_returns(returns, horizon=horizon)

    return list(stat_function(subset_returns))


def distribution_of_statistic(
    returns, stat_function, monte_length=1000, horizon=None, colnames=None
):

    if colnames is None:
        colnames = list(returns.columns)

    if horizon is None:
        horizon = len(returns.index)

    list_of_bs_stats = []
    thing = progressBar(monte_length)
    for notUsed in range(monte_length):
        list_of_bs_stats.append(
            statistic_from_bootstrap(returns, stat_function, horizon=horizon)
        )
        thing.iterate()

    ans = pd.DataFrame(np.array(list_of_bs_stats))
    ans = pd.DataFrame(ans)
    ans.columns = colnames

    return ans


def optimisation_override_sharpe_ratio(
    returns, instrument_to_override="", value_to_use=np.nan
):
    corrmatrix = returns.corr().values
    mean_list = list(annualised_mean(returns).values)
    stdev_list = list(annualised_std(returns).values)

    instrument_codes = list(returns.columns)
    assert instrument_to_override in instrument_codes
    index_of_instrument = instrument_codes.index(instrument_to_override)

    mean_list[index_of_instrument] = value_to_use * \
        stdev_list[index_of_instrument]

    return optimisation_with_data(corrmatrix, mean_list, stdev_list)


def optimisation_override_stdev(
    returns, instrument_to_override="", value_to_use=np.nan
):
    corrmatrix = returns.corr().values
    mean_list = list(annualised_mean(returns).values)
    stdev_list = list(annualised_std(returns).values)

    instrument_codes = list(returns.columns)
    assert instrument_to_override in instrument_codes
    index_of_instrument = instrument_codes.index(instrument_to_override)

    stdev_list[index_of_instrument] = value_to_use

    return optimisation_with_data(corrmatrix, mean_list, stdev_list)


def optimisation_override_corr(
        returns,
        instrument_to_override="",
        value_to_use=np.nan):
    corrmatrix = returns.corr().values
    mean_list = list(annualised_mean(returns).values)
    stdev_list = list(annualised_std(returns).values)

    assert instrument_to_override in corr_pairs

    instrument_codes = list(returns.columns)

    codes_in_pair_name = instrument_to_override.split("/")

    first_instrument_code = codes_in_pair_name[0]
    second_instrument_code = codes_in_pair_name[1]
    index_of_instrument_one = instrument_codes.index(first_instrument_code)
    index_of_instrument_two = instrument_codes.index(second_instrument_code)

    corrmatrix[index_of_instrument_one][index_of_instrument_two] = value_to_use
    corrmatrix[index_of_instrument_two][index_of_instrument_one] = value_to_use

    return optimisation_with_data(corrmatrix, mean_list, stdev_list)


def get_weights_from_distribution_of_stat(
    returns,
    stat_name="Sharpe Ratio",
    stat_function=sharpe_ratio,
    instrument_to_override="",
    colnames=None,
    opt_overide=optimisation_override_sharpe_ratio,
    bins=50,
    monte_length=1000,
):

    stat_distr = distribution_of_statistic(
        returns, stat_function, monte_length, colnames=colnames
    )
    stat_distr = stat_distr[instrument_to_override]

    avg_value = stat_function(returns)
    avg_value_instrument = avg_value[instrument_to_override]

    hist_points = list(np.histogram(stat_distr, bins=bins)[1])
    optimal_weights = [
        opt_overide(returns, instrument_to_override, value_to_use)
        for value_to_use in hist_points
    ]
    optimal_weights = pd.DataFrame(optimal_weights)
    optimal_weights.columns = returns.columns
    optimal_weights.index = hist_points

    subplot(2, 1, 1)
    title(
        "Distribution of %s for %s, average %.2f"
        % (stat_name, instrument_to_override, avg_value_instrument)
    )
    hist(stat_distr, bins=bins)
    subplot(2, 1, 2)
    optimal_weights.plot(ax=gca())

    return (stat_distr, optimal_weights)


get_weights_from_distribution_of_stat(
    returns, instrument_to_override="US5", bins=50, monte_length=10000
)
get_weights_from_distribution_of_stat(
    returns,
    instrument_to_override="SP500",
    bins=50,
    monte_length=10000,
    stat_name="Stdev",
    stat_function=annualised_std,
    opt_overide=optimisation_override_stdev,
)

x = get_weights_from_distribution_of_stat(
    returns,
    instrument_to_override="SP500/US5",
    bins=50,
    monte_length=10000,
    stat_name="Correlation",
    stat_function=corr_as_vector,
    opt_overide=optimisation_override_corr,
    colnames=corr_pairs,
)

# Bootstrap from distribution of estimates
# Repeatedly draw from the distr

monte_length = 5000
monte_length_inside = 100
SR_distr = distribution_of_statistic(returns, sharpe_ratio, monte_length)
stdev_distr = distribution_of_statistic(returns, annualised_std, monte_length)
corr_dist = distribution_of_statistic(returns, corr_as_vector, monte_length)


def from_cor_vec_to_matrix(corrvec):
    corrmatrix = pd.DataFrame(
        index=["SP500", "US10", "US5"], columns=["SP500", "US10", "US5"]
    )
    corrmatrix.iloc[0][0] = 1.0
    corrmatrix.iloc[0][1] = corrvec[1]
    corrmatrix.iloc[0][2] = corrvec[0]
    corrmatrix.iloc[1][0] = corrvec[1]
    corrmatrix.iloc[1][1] = 1.0
    corrmatrix.iloc[1][2] = corrvec[2]
    corrmatrix.iloc[2][0] = corrvec[0]
    corrmatrix.iloc[2][1] = corrvec[2]
    corrmatrix.iloc[2][2] = 1.0

    return corrmatrix


monte_length_inside = 5000
weights = []
thing = progressBar(monte_length_inside)

for notUsed in range(monte_length_inside):

    corrvec = corr_dist.iloc[int(random.uniform(0, len(corr_dist)))]
    srlist = SR_distr.iloc[int(random.uniform(0, len(corr_dist)))]
    stdev_list = stdev_distr.iloc[int(random.uniform(0, len(corr_dist)))]
    corrmatrix = from_cor_vec_to_matrix(corrvec)
    meanlist = srlist * stdev_list

    weights.append(
        optimisation_with_data(
            corrmatrix.values,
            list(meanlist),
            list(stdev_list)))
    thing.iterate()

weights = pd.DataFrame(weights, columns=["SP500", "US10", "US5"])

hist(weights.SP500, bins=50)

opt_lev_dist = distribution_of_statistic(
    pd.DataFrame(portfolio), optimal_leverage, monte_length=5000
)


# cool model free technique
def filter_weight(wts):
    if sum(wts) > 1.001 or sum(wts) < 0.999:
        return False
    return True


poss_weights = np.arange(0.0, 1.0, 0.01)

# method 2
list_of_poss_weights = []
idx_of_poss_weights = []
for spidx, sp500wt in enumerate(poss_weights):
    for us10idx, us10wt in enumerate(poss_weights):
        for us5idx, us5wt in enumerate(poss_weights):
            wts = [sp500wt, us10wt, us5wt]
            idx = [spidx, us10idx, us5idx]
            if filter_weight(wts):
                list_of_poss_weights.append(wts)
                idx_of_poss_weights.append(idx)

thing = progressBar(len(list_of_poss_weights), show_each_time=True)

results_distr = []
for weight_to_consider in list_of_poss_weights:
    weekly_returns_to_use = (
        weight_to_consider[0] * returns.SP500
        + weight_to_consider[1] * returns.US10
        + weight_to_consider[2] * returns.US5
    )
    distr = distribution_of_final_values_bootstrapped(
        weekly_returns_to_use, monte_count=500, years=30
    )
    results_distr.append(distr)
    thing.iterate()

perc_point = 25

results = []
for distr in results_distr:
    point_of_interest = np.percentile(distr, perc_point)
    # point_of_interest = np.mean(distr)
    results.append(point_of_interest)

print(list_of_poss_weights[results.index(max(results))])

# plot them
results_as_matrix = np.empty([len(poss_weights), len(poss_weights)])
results_as_matrix[:] = np.nan
for this_idx_of_weights, the_result in zip(idx_of_poss_weights, results):
    # we can only do this as weights add up to 1, so 2x2 array works
    results_as_matrix[this_idx_of_weights[0]
                      ][this_idx_of_weights[1]] = the_result

import matplotlib.pyplot as plt

plt.contourf(results_as_matrix)
plt.colorbar()

plt.xlabel("US 10 year")
plt.ylabel("SP500")
