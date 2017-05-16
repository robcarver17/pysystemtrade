from syscore.pdutils import pd_readcsv_frompackage
from syscore.genutils import progressBar
from copy import copy
from scipy.stats import norm
import matplotlib.mlab as mlab
import matplotlib.cm as cm

import pandas as pd
import numpy as np
from sysdata.csvdata import csvFuturesData
import matplotlib.pyplot as plt

def process_row(x):
    try:
        return float(x[0])
    except:
        return np.nan


def get_vix_data():
    vix_spot=pd_readcsv_frompackage("examples.vix.VIX.csv")

    return pd.Series([process_row(x) for x in vix_spot.values], vix_spot.index).ffill()

def get_us_long_data():
    us_long_data = pd_readcsv_frompackage("examples.vix.US_monthly_returns.csv")
    return us_long_data

# functions to do conditional binning
def half_split(conditioner):
    binrange = [[conditioner.min(), conditioner.median()], [conditioner.median(), conditioner.max()]]
    return binrange

def deciles(conditioner):
    return [[conditioner.min(), np.percentile(conditioner.values, 10)], [np.percentile(conditioner.values, 90), conditioner.max()]]

def deciles_and_mid(conditioner):
    return [[conditioner.min(), np.percentile(conditioner.values, 10)],
            [np.percentile(conditioner.values, 10), np.percentile(conditioner.values, 90)],
            [np.percentile(conditioner.values, 90), conditioner.max()]]

def no_binning(conditioner):
    return [[conditioner.min(),  conditioner.max()]]

def below_10(conditioner):
    return [[conditioner.min(),  10.0], [10.0,  conditioner.max()]]

# actually do the analysis

def produce_conditioned_distributions(conditioner, bin_func, response_change):
    conditioner_cleaned = conditioner.dropna()
    my_bins=bin_func(conditioner_cleaned)

    binned_response = [response_change[(conditioner>bin[0]) & (conditioner<=bin[1])].values for bin in my_bins]

    binned_response = [[x for x in bin_data if not np.isnan(x)] for bin_data in binned_response]

    my_bin_labels = ["%.2f to %.2f" % (bin[0], bin[1]) for bin in my_bins]

    return (my_bin_labels, binned_response)



def do_a_plot(response_variable, conditioner, lag_response=True, frequency="D", time_horizon=30, bin_func=no_binning,
              calculate_sharpe_ratios=False,
              index_to_use = None, drawfittedlines=False, target_in_bin=20,
              calculate_returns = True):

    response_variable = copy(response_variable)
    conditioner = copy(conditioner)

    if lag_response:
        conditioner = conditioner.shift(1)

    if index_to_use is None:
        index_to_use = response_variable.index

    conditioner = conditioner.reindex(index_to_use)
    response_variable = response_variable.reindex(index_to_use)


    conditioner=conditioner.resample(frequency).last().ffill()
    response_variable=response_variable.resample(frequency).last().ffill()

    if calculate_returns:
        response_variable = (response_variable.shift(-time_horizon) - response_variable) /response_variable
    else:
        response_variable = response_variable.shift(-time_horizon)

    if calculate_sharpe_ratios:
        annualisation = (time_horizon / 250)**.5
        vol = pd.rolling_std(response_variable, time_horizon)
        response_variable = response_variable / vol.shift(-time_horizon)
        response_variable = response_variable * annualisation


    (my_bin_labels, bin_data) = produce_conditioned_distributions(conditioner, bin_func, response_variable)

    colors = ["red", "blue", "green"]
    all_bin_range = np.max(np.max(np.array(bin_data))) - np.min(np.min(np.array(bin_data)))
    desired_bin_count = sum([len(x) for x in bin_data]) / target_in_bin
    desired_bin_width = all_bin_range / desired_bin_count

    for my_color, one_bin in zip(colors, bin_data):
        nrange = np.max(one_bin) - np.min(one_bin)
        bin_count = int(nrange / desired_bin_width)
        n, bins, patches = plt.hist(one_bin, bin_count, facecolor=my_color, alpha=0.5)

        if drawfittedlines:
            (mu, sigma) = norm.fit(one_bin)
            y = mlab.normpdf( bins, mu, sigma)
            l = plt.plot(bins, y, color=my_color, linewidth=2)


    plt.legend(my_bin_labels)
    plt.show()
    meanstring=["%.5f (%s) " % (np.mean(one_bin), bin_label) for one_bin, bin_label in zip(bin_data, my_bin_labels)]
    print("Means %s" % "".join(meanstring))

    return bin_data

def _sample_this(thingtosample, sample_length):
    indices= [int(np.random.uniform() * len(thingtosample)) for notused in range(sample_length)]
    return [thingtosample[idx] for idx in indices]

def paired_test(bin_data, number_of_runs=200):

    sample_length=np.min([len(onebin) for onebin in bin_data])

    diffs = []
    pb=progressBar(number_of_runs)
    for notUsed in range(number_of_runs):
        first_sample = _sample_this(bin_data[0], sample_length)
        second_sample = _sample_this(bin_data[1], sample_length)
        sample_diff = [x-y for x,y in zip(first_sample, second_sample)]

        this_difference = np.mean(sample_diff)
        diffs.append(this_difference)
        pb.iterate()

    return diffs

def plot_paired_test(bin_data, number_of_runs=200):
    diff_dist = paired_test(bin_data, number_of_runs=number_of_runs)
    bin_count = int(number_of_runs/50)
    plt.hist(diff_dist, bin_count)
    legend_string = "Mean difference %.5f" % np.mean(diff_dist)
    plt.title(legend_string)
    plt.show()

    count_positive = len([x for x in diff_dist if x>0.0])
    count_fraction = float(count_positive) / len(diff_dist)

    print("Proportion positive %.5f" % count_fraction)

# get data
vix_spot=get_vix_data()

my_data_handler=csvFuturesData()

sp500future = my_data_handler.get_raw_price("SP500")
vixfuture = my_data_handler.get_raw_price("VIX")

# we don't use this, but can check the results with it
# note this is monthly data
# You'd need to adjust 'frequency' and time_horizon appropriately
usequitylong = get_us_long_data().USA_TR



vix_spot.plot()
plt.show()

# start with unconditional plot

do_a_plot(sp500future, vix_spot, lag_response=False, frequency="D", time_horizon=20, bin_func=no_binning,
              index_to_use = None, drawfittedlines=False)

# add conditioning, half and half
bin_data=do_a_plot(sp500future, vix_spot, lag_response=True, frequency="D", time_horizon=20, bin_func=half_split,
              index_to_use = None, drawfittedlines=False)

plot_paired_test(bin_data, number_of_runs=5000)

# add conditioning, half and half, with SR
bin_data=do_a_plot(sp500future, vix_spot, lag_response=True, frequency="D", time_horizon=20, bin_func=half_split,
              index_to_use = None, drawfittedlines=False, calculate_sharpe_ratios=True)

plot_paired_test(bin_data, number_of_runs=5000)

# below 10
bin_data=do_a_plot(sp500future, vix_spot, lag_response=True, frequency="D", time_horizon=20, bin_func=below_10,
              index_to_use = None, drawfittedlines=False, calculate_sharpe_ratios=True)

plot_paired_test(bin_data, number_of_runs=5000)


# deciles and middle
# this is for the plot
bin_data=do_a_plot(sp500future, vix_spot, lag_response=True, frequency="D", time_horizon=20, bin_func=deciles_and_mid,
              index_to_use = None, drawfittedlines=False, calculate_sharpe_ratios=True)

plot_paired_test([bin_data[0], bin_data[1]], number_of_runs=5000)
plot_paired_test([bin_data[1], bin_data[2]], number_of_runs=5000)
plot_paired_test([bin_data[0], bin_data[2]], number_of_runs=5000)

###
one_month_vol = pd.rolling_std(sp500future.diff(), 20)

bin_data=do_a_plot(one_month_vol, vix_spot, lag_response=True, frequency="D", time_horizon=20, bin_func=deciles_and_mid,
              calculate_sharpe_ratios=False, calculate_returns=False)

plot_paired_test([bin_data[0], bin_data[1]], number_of_runs=5000)
plot_paired_test([bin_data[1], bin_data[2]], number_of_runs=5000)
plot_paired_test([bin_data[0], bin_data[2]], number_of_runs=5000)


one_month_vol = pd.rolling_std(sp500future.diff(), 20)

bin_data=do_a_plot(one_month_vol, vix_spot, lag_response=True, frequency="D", time_horizon=20, bin_func=deciles_and_mid,
              calculate_sharpe_ratios=False, calculate_returns=False)

plot_paired_test([bin_data[0], bin_data[1]], number_of_runs=5000)
plot_paired_test([bin_data[1], bin_data[2]], number_of_runs=5000)
plot_paired_test([bin_data[0], bin_data[2]], number_of_runs=5000)

one_month_vol = pd.rolling_std(sp500future.diff(), 20)




bin_data=do_a_plot(vix_spot, vix_spot, lag_response=True, frequency="D", time_horizon=500, bin_func=deciles_and_mid,
              calculate_sharpe_ratios=False, calculate_returns=False)

plot_paired_test([bin_data[0], bin_data[1]], number_of_runs=5000)
plot_paired_test([bin_data[1], bin_data[2]], number_of_runs=5000)
plot_paired_test([bin_data[0], bin_data[2]], number_of_runs=5000)
