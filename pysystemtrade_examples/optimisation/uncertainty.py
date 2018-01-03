from syscore.genutils import progressBar
from sysdata.csvdata import csvFuturesData
import pandas as pd
import random
from syscore.optimisation import optimise, sigma_from_corr_and_std
import numpy as np
from matplotlib.pyplot import show, legend
from syscore.correlations import boring_corr_matrix, get_avg_corr

# get some returns to play with
# 3 asset problem

data=csvFuturesData()

def calc_weekly_return(instrument_code, start_date=pd.datetime(1998,1,1)):
    price = data[instrument_code]
    price=price[start_date:]
    weekly_price = price.resample("W").last()
    denom_price = data.get_instrument_raw_carry_data(instrument_code).PRICE
    denom_weekly_price = denom_price.reindex(weekly_price.index, method="ffill")

    weekly_returns = (weekly_price - weekly_price.shift(1))/denom_weekly_price

    return weekly_returns[1:]

code_list = ["SP500", "US10", "US5"]
corr_pairs = ["SP500/US5", "SP500/US10", "US5/US10"]

returns = dict([(instrument_code, calc_weekly_return(instrument_code)) for instrument_code in code_list])
returns = pd.DataFrame(returns)


def some_random_bootstrapped_returns(returns, horizon=None):
    if horizon is None:
        horizon = len(returns.index)

    draws = [int(random.uniform(0, len(returns))) for notused in range(horizon)]

    return returns.iloc[draws,]

def statistic_from_bootstrap(returns, stat_function, horizon=None):

    subset_returns = some_random_bootstrapped_returns(returns, horizon=horizon)

    return list(stat_function(subset_returns))

def distribution_of_statistic(returns, stat_function, monte_length=1000, horizon=None, colnames=code_list):
    list_of_bs_stats = []
    thing=progressBar(monte_length)
    for notUsed in range(monte_length):
        list_of_bs_stats.append(statistic_from_bootstrap(returns, stat_function, horizon=horizon))
        thing.iterate()

    ans=pd.DataFrame(np.array(list_of_bs_stats))
    ans.columns = colnames

    return ans

def sharpe_ratio(weekly_returns):
    return annualised_mean(weekly_returns) / annualised_std(weekly_returns)

def annualised_mean(weekly_returns):
    return (weekly_returns.mean()*52.0)

def annualised_std(weekly_returns):
    return (weekly_returns.std()*(52**.5))

def corr_as_vector(weekly_returns):
    corr = weekly_returns.corr()
    return [corr[code_list[0]][code_list[2]], corr[code_list[0]][code_list[1]], corr[code_list[1]][code_list[2]]]

def optimisation(weekly_returns, equalisecorr=False, equaliseSR=False, riskweights=False):
    if equalisecorr:
        corrmatrix = np.diag([1.0]*len(returns.columns))
    else:
        corrmatrix = weekly_returns.corr().values
    mean_list = list(annualised_mean(weekly_returns).values)
    stdev_list = list(annualised_std(weekly_returns).values)

    if equaliseSR:
        sr_list = [each_return / each_std for each_return, each_std in zip(mean_list, stdev_list)]

        avg_sr = np.nanmean(sr_list)
        mean_list = [each_std * avg_sr for each_std in stdev_list]

    if riskweights:
        avg_std = np.nanmean(stdev_list)
        mean_list = [this_mean * avg_std / this_std for this_mean, this_std in zip(mean_list, stdev_list)]
        stdev_list = [avg_std]*len(stdev_list)

    return optimisation_with_data(corrmatrix, mean_list, stdev_list)

def optimisation_with_data(corrmatrix, mean_list, stdev_list):
    sigma = sigma_from_corr_and_std(stdev_list, corrmatrix)

    weights = optimise(sigma, mean_list)

    return weights


cset=["red","blue","green","black", "yellow"]

annualised_mean(returns)
annualised_std(returns)
sharpe_ratio(returns)
corr_as_vector(returns)
optimisation(returns)

"""
Equalisation
"""

optimisation(returns, equalisecorr=False, equaliseSR=True)
optimisation(returns, equalisecorr=True, equaliseSR=False)
optimisation(returns, riskweights=True)
optimisation(returns, equalisecorr=False, equaliseSR=True, riskweights=True)
optimisation(returns, equalisecorr=True, equaliseSR=False, riskweights=True)
optimisation(returns, equalisecorr=True, equaliseSR=True, riskweights=True)

ans_mean=distribution_of_statistic(returns, annualised_mean, colnames=code_list, monte_length=10000)
print(ans_mean.quantile(0.1))
print(ans_mean.quantile(0.9))
for color, cname in zip(cset,code_list):
    ans_mean[cname].hist(bins=50, color=color, histtype='step', alpha=.5)
legend(code_list)
show()

ans_std=distribution_of_statistic(returns, annualised_std, colnames=code_list,monte_length=10000)
print(ans_std.quantile(0.1))
print(ans_std.quantile(0.9))
for color, cname in zip(cset,code_list):
    ans_std[cname].hist(bins=50, color=color, histtype='step', alpha=.5)
legend(code_list)
show()

ans_sr=distribution_of_statistic(returns, sharpe_ratio, colnames=code_list, monte_length=10000)
print(ans_sr.quantile(0.1))
print(ans_sr.quantile(0.9))
for color, cname in zip(cset,code_list):
    ans_sr[cname].hist(bins=50, color=color, histtype='step', alpha=.5)

legend(code_list)
show()

ans_corr=distribution_of_statistic(returns, corr_as_vector, colnames=corr_pairs, monte_length=10000)
for color, cname in zip(cset,corr_pairs):
    ans_corr[cname].hist(bins=50, color=color, histtype="step", alpha=.5)
print(ans_corr.quantile(0.1))
print(ans_corr.quantile(0.9))

legend(corr_pairs)
show()

# get rolling estimates over time
def get_rolling_estimate(returns, func_name, value_index=0, monte_length=1000):
    slice_end=pd.date_range(returns.index[1], returns.index[-1], freq="12M")
    thing=progressBar(len(slice_end))

    lower_points=[]
    upper_points=[]
    for end_point in slice_end:
        subset_returns = returns[:end_point]
        subset_distribution = distribution_of_statistic(subset_returns, func_name,  monte_length=monte_length)
        lower_points.append(subset_distribution.quantile(0.1)[value_index])
        upper_points.append(subset_distribution.quantile(0.9)[value_index])
        thing.iterate()

    output = pd.DataFrame(dict(upper=upper_points, lower=lower_points), index=slice_end)

    return output

sr_5y= get_rolling_estimate(returns, sharpe_ratio, monte_length=1000, value_index=2)
std_5y=get_rolling_estimate(returns, annualised_std, monte_length=1000, value_index=2)
corr_5y_sp=get_rolling_estimate(returns, corr_as_vector, monte_length=1000, value_index=0)

# check upper and lower boundaries
corrmatrix = returns.corr().values
mean_list = list(annualised_mean(returns).values)
stdev_list = list(annualised_std(returns).values)

# tweak these to get extreme results
corrmatrix[0][2] = corrmatrix[2][0] = ans_corr.quantile(0.9)[0]
mean_list[0]=ans_mean.quantile(0.9)[0]
mean_list[2]=ans_mean.quantile(0.1)[2]

stdev_list[0]=ans_std.quantile(0.9)[0]

print(optimisation_with_data(corrmatrix, mean_list, stdev_list))

# Generate some fake data to illustrate bootstrapping
def threeassetportfolio(yearsdata=30, SRlist=[0.5, 0.5, 0.5], annual_vol=[.15,.15,.15], clist=[.0, .0, .0],
                        index_start=pd.datetime(2000, 1, 1)):

    plength = yearsdata * 52
    (c1, c2, c3) = clist
    dindex = pd.date_range(index_start, periods=plength, freq="W")

    daily_vol = [vol_item / 16.0 for vol_item in annual_vol]
    means = [SR_item * vol_item / 250.0 for SR_item, vol_item in zip(SRlist, annual_vol)]
    stds = np.diagflat(daily_vol)
    corr = np.array([[1.0, c1, c2], [c1, 1.0, c3], [c2, c3, 1.0]])

    covs = np.dot(stds, np.dot(corr, stds))
    plength = len(dindex)

    m = np.random.multivariate_normal(means, covs, plength).T

    portreturns = pd.DataFrame(dict(one=m[0], two=m[1], three=m[2]), dindex)
    portreturns = portreturns[['one', 'two', 'three']]

    # adjust targets for mean
    avgs = list(portreturns.mean())
    differential = [avg_item - mean_item for avg_item, mean_item in zip(avgs, means)]
    differential = pd.DataFrame([differential]*len(portreturns.index), portreturns.index, columns=portreturns.columns)

    portreturns = portreturns - differential

    return portreturns

fake_data1=threeassetportfolio()
fake_data2=threeassetportfolio(SRlist=[0.5, 0.5, 0.0], annual_vol=[.1,.1,.2], clist=[.9, .0, .0])

def rolling_optimisation(weekly_returns, opt_function=optimisation, **kwargs):
    slice_ends = pd.date_range(returns.index[1], returns.index[-1], freq="12M")
    weights=[]
    thing=progressBar(len(slice_ends))

    for end_point in slice_ends:
        subset_data = weekly_returns[:end_point]
        period_weights = opt_function(subset_data, **kwargs)
        weights.append(period_weights)
        thing.iterate()

    weights=pd.DataFrame(weights, index=slice_ends, columns=weekly_returns.columns)

    return  weights

def bootstrapped_optimisation(weekly_returns, monte_carlo=1000, **kwargs):
    weights=[]
    for notUsed in range(monte_carlo):
        sampled_data=some_random_bootstrapped_returns(weekly_returns)
        sample_weights = optimisation(sampled_data, **kwargs)
        weights.append(sample_weights)

    weights=np.array(weights)
    avg_weights = weights.mean(axis=0)
    avg_weights = list(avg_weights)

    return avg_weights

rolling_optimisation(fake_data1).plot()
rolling_optimisation(fake_data2).plot()

rolling_optimisation(fake_data1, bootstrapped_optimisation).plot()
rolling_optimisation(fake_data2, bootstrapped_optimisation).plot()

# real data
rolling_optimisation(returns, bootstrapped_optimisation).plot()

# conditional

def measure_12_month_momentum(weekly_returns):
    return_last_year = 52.0*weekly_returns.rolling(center=False, window=52, min_periods=1).mean()
    std_last_year = (52.0**.5)*weekly_returns.rolling(center=False, window=52, min_periods=1).std()
    sr_last_year = return_last_year / std_last_year

    return sr_last_year

def measure_abs_momentum(weekly_returns):
    code_list = weekly_returns.columns
    abs_mom={}
    for code in code_list:
        abs_mom[code] = measure_12_month_momentum(weekly_returns[code])

    abs_mom_all = pd.DataFrame(abs_mom)

    return abs_mom_all

# we don't use this function, but it could be useful
def measure_relative_momentum(weekly_returns):

    abs_mom_all = measure_abs_momentum(weekly_returns)
    abs_mom_avg = abs_mom_all.mean(axis=1)

    rel_mom=dict([(code, abs_mom_all[code]-abs_mom_avg) for code in code_list])
    rel_mom = pd.DataFrame(rel_mom)

    return rel_mom


def subset_data_by_momentum_range(weekly_returns,  mrange=[-999, -2.0]):

    mom_estimates = measure_abs_momentum(weekly_returns)
    mom_estimates = mom_estimates.shift(1)

    subset_data_list=[]
    for code in weekly_returns.columns:
        mom_estimates_instrument = mom_estimates[code]
        subset_data_for_instrument=weekly_returns[code]
        subset_data = subset_data_for_instrument[mom_estimates_instrument>mrange[0]]
        subset_data = subset_data[mom_estimates_instrument<=mrange[1]]

        subset_data_list.append(subset_data)

    subset_data_as_pd=pd.concat(subset_data_list, axis=0)

    return subset_data

def distribution_by_momentum_range(weekly_returns,  stat_function, mrange=[-999, -2.0]):
    subset_returns = pd.DataFrame(subset_data_by_momentum_range(weekly_returns, mrange=mrange))
    distr = distribution_of_statistic(subset_returns, stat_function, colnames=["%2.f:%.2f" % (mrange[0], mrange[1])])

    return distr



all = distribution_by_momentum_range(returns, sharpe_ratio, mrange=[-999, 999]).iloc[:,0].values

# points taken off distribution of abs_mom: 10,25,75,90
#sr_dist_very_low = distribution_by_momentum_range(returns, sharpe_ratio, mrange=[-999, -0.75]).iloc[:,0].values
#sr_dist_low = distribution_by_momentum_range(returns, sharpe_ratio, mrange=[-0.75, -0.05]).iloc[:,0].values
#sr_dist_middle = distribution_by_momentum_range(returns, sharpe_ratio, mrange=[-0.05, 1.25]).iloc[:,0].values
#sr_dist_high = distribution_by_momentum_range(returns, sharpe_ratio, mrange=[1.25, 1.85]).iloc[:,0].values
#sr_dist_very_high = distribution_by_momentum_range(returns, sharpe_ratio, mrange=[1.85, 999]).iloc[:,0].values

sr_dist_low = distribution_by_momentum_range(returns, sharpe_ratio, mrange=[-0.75, -0.05]).iloc[:,0].values
sr_dist_high = distribution_by_momentum_range(returns, sharpe_ratio, mrange=[1.25, 1.85]).iloc[:,0].values

#sr_conditional = dict(Very_low = sr_dist_very_low, Low=sr_dist_low, Middle=sr_dist_middle,
#                      High=sr_dist_high, Very_high=sr_dist_very_high)

sr_conditional = dict(low = sr_dist_low, high=sr_dist_high)

cond_names = list(sr_conditional.keys())

sr_conditional = pd.DataFrame(sr_conditional, index=range(len(sr_conditional[cond_names[0]])))

for color, cond_name in zip(cset,cond_names):
    ans=sr_conditional[cond_name]
    ans.hist(bins=50, color=color, histtype='step', alpha=.5)

legend(cond_names)
show()

# used to calculate conditional bootstrap estimates

def distances(weekly_returns):
    mom_estimates = measure_abs_momentum(weekly_returns)
    mom_estimates = mom_estimates.shift(1)
    all_distances={}
    for code in mom_estimates.keys():
        this_code_distance=[]
        for date_index_value, value in zip(mom_estimates.index, mom_estimates[code]):
            this_value_distance=get_distance_versus_value(value, mom_estimates, date_index_value)
            this_code_distance.append(this_value_distance)
        all_distances[code]=this_code_distance

    return all_distances

def get_distance_versus_value(value, mom_estimates, date_index_value):
    pass

def single_value_calc(value, other_value):
    return 1 / abs(1+value - other_value)

### risk weighting plus bayesian

def optimisation_bayesian_riskweights(weekly_returns, shrinkcorr=0.0, shrinkSR=0.0, priorcorroffdiag=0.5,
                                      priorSR=0.25):

    prior_corrmatrix = boring_corr_matrix(len(weekly_returns.columns), priorcorroffdiag)

    est_corrmatrix = weekly_returns.corr().values

    shrink_corrmatrix = (prior_corrmatrix*shrinkcorr)+(est_corrmatrix*(1-shrinkcorr))

    est_mean_list = list(annualised_mean(weekly_returns).values)
    est_stdev_list = list(annualised_std(weekly_returns).values)

    est_sr_list = [each_return / each_std for each_return, each_std in zip(est_mean_list, est_stdev_list)]
    prior_sr_list = [priorSR] * len(est_sr_list)

    shrink_sr_list = [(prior*shrinkSR)+(est*(1-shrinkSR)) for prior, est in zip(prior_sr_list, est_sr_list)]

    shrunk_mean_list = [each_std * shrunk_sr for each_std, shrunk_sr in zip(est_stdev_list, shrink_sr_list)]

    ## apply risk weights
    avg_std = np.nanmean(est_stdev_list)
    riskwt_mean_list = [this_mean * avg_std / this_std for this_mean, this_std in zip(shrunk_mean_list, est_stdev_list)]
    norm_stdev_list = [avg_std]*len(est_stdev_list)

    return optimisation_with_data(shrink_corrmatrix, riskwt_mean_list, norm_stdev_list)


for shrinkcorr in [0.0,.25,.5,.75,1.0]:
    for shrinkSR in [0.0,.25,.5,.75,1.0]:
        print("\nSR %f corr %f" % (shrinkSR, shrinkcorr))
        print("weights:")
        print(optimisation_bayesian_riskweights(returns, shrinkcorr=shrinkcorr, shrinkSR=shrinkSR))

## bootstrapping over time with risk weights
ans=rolling_optimisation(returns, bootstrapped_optimisation, riskweights=True)
ans2=rolling_optimisation(returns, bootstrapped_optimisation, riskweights=False)
ans3=rolling_optimisation(returns, bootstrapped_optimisation, riskweights=True, equaliseSR=True)

## bayesian
ans4= rolling_optimisation(returns, optimisation_bayesian_riskweights, shrinkcorr=0.5, shrinkSR=0.95)