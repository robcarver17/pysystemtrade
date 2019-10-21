import numpy as np
import random
import matplotlib
import pandas as pd
matplotlib.use("TkAgg")


from systems.provided.futures_chapter15.estimatedsystem import *
system = futures_system()

del(system.config.instruments) # so we can get results for everything

instrument_codes = system.get_instrument_list()

percentage_returns = dict()

for code in instrument_codes:
    denom_price = system.rawdata.daily_denominator_price(code)
    instr_prices = system.rawdata.get_daily_prices(code)

    num_returns = instr_prices.diff()
    perc_returns = num_returns / denom_price.ffill()

    vol_norm_returns = system.rawdata.norm_returns(code)
    perc_returns[abs(vol_norm_returns)>10]=np.nan

    percentage_returns[code] = perc_returns

for code in instrument_codes:
    print(code)
    print(percentage_returns[code].skew())


def resampled_skew_estimator(data, monte_carlo_count=500):
    """
    Get a distribution of skew estimates

    :param data: some time series
    :param monte_carlo_count: number of goes we monte carlo for
    :return: list
    """

    skew_estimate_distribution = []
    for _notUsed in range(monte_carlo_count):
        resample_index = [int(random.uniform(0,len(data))) for _alsoNotUsed in range(len(data))]
        resampled_data = data[resample_index]
        sample_skew_estimate = resampled_data.skew()
        skew_estimate_distribution.append(sample_skew_estimate)

    return skew_estimate_distribution




data = percentage_returns['VIX']
x=resampled_skew_estimator(data, 1000)

import matplotlib.pyplot as pyplot
pyplot.rcParams.update({'font.size': 16})

pyplot.hist(x, bins=30)

# do a boxplot for everything
import pandas as pd

df_skew_distribution = dict()
for code in instrument_codes:
    print(code)
    x = resampled_skew_estimator(percentage_returns[code],1000)
    y = pd.Series(x)
    df_skew_distribution[code]=y

df_skew_distribution = pd.DataFrame(df_skew_distribution)

df_skew_distribution = df_skew_distribution.reindex(df_skew_distribution.mean().sort_values().index, axis=1)

df_skew_distribution.boxplot()
pyplot.xticks(rotation=90)

# average return vs skew
avg_returns = [percentage_returns[code].mean() for code in instrument_codes]
skew_list = [percentage_returns[code].skew() for code in instrument_codes]

fig, ax = pyplot.subplots()
ax.scatter(skew_list, avg_returns, marker="")

for i, txt in enumerate(instrument_codes):
    ax.annotate(txt, (skew_list[i], avg_returns[i]))


def resampled_mean_estimator(data, monte_carlo_count=500):
    """
    Get a distribution of mean estimates

    :param data: some time series
    :param monte_carlo_count: number of goes we monte carlo for
    :return: list
    """

    mean_estimate_distribution = []
    for _notUsed in range(monte_carlo_count):
        resample_index = [int(random.uniform(0, len(data))) for _alsoNotUsed in range(len(data))]
        resampled_data = data[resample_index]
        sample_mean_estimate = resampled_data.mean()
        mean_estimate_distribution.append(sample_mean_estimate)

    return mean_estimate_distribution


df_mean_distribution = dict()
for code in instrument_codes:
    print(code)
    x = resampled_mean_estimator(percentage_returns[code],1000)
    y = pd.Series(x)
    df_mean_distribution[code]=y

df_mean_distribution = pd.DataFrame(df_mean_distribution)

df_mean_distribution = df_mean_distribution[df_skew_distribution.columns]

df_mean_distribution.boxplot()
pyplot.xticks(rotation=90)

skew_by_code = df_skew_distribution.mean()
avg_skew = np.mean(skew_by_code.values)
low_skew_codes = list(skew_by_code[skew_by_code<avg_skew].index)
high_skew_codes = list(skew_by_code[skew_by_code>=avg_skew].index)

def resampled_mean_estimator_multiple_codes(percentage_returns, code_list, monte_carlo_count=500, avoiding_vol=False):
    """

    :param percentage_returns: dict of returns
    :param code_list: list of str, a subset of percentage_returns.keys
    :param monte_carlo_count: how many times
    :return: list of mean estimtes
    """

    mean_estimate_distribution = []
    for _notUsed in range(monte_carlo_count):
        # randomly choose a code
        # comment in these lines to avoid vol
        if avoiding_vol:
            code = "VIX"
            while code in ["VIX", "V2X"]:
                code = code_list[int(random.uniform(0, len(code_list)))]
        else:
            code = code_list[int(random.uniform(0, len(code_list)))]

        data = percentage_returns[code]
        resample_index = [int(random.uniform(0,len(data))) for _alsoNotUsed in range(len(data))]
        resampled_data = data[resample_index]
        sample_mean_estimate = resampled_data.mean()
        mean_estimate_distribution.append(sample_mean_estimate)

    return mean_estimate_distribution


df_mean_distribution_multiple = dict()
df_mean_distribution_multiple['High skew'] = resampled_mean_estimator_multiple_codes(percentage_returns,high_skew_codes,1000)
df_mean_distribution_multiple['Low skew'] = resampled_mean_estimator_multiple_codes(percentage_returns,low_skew_codes,1000)

df_mean_distribution_multiple = pd.DataFrame(df_mean_distribution_multiple)
df_mean_distribution_multiple.boxplot()


# now risk adjusted returns

# sharpe ratio  vs skew
sharpe_ratios = [16.0*percentage_returns[code].mean()/percentage_returns[code].std() for code in instrument_codes]
skew_list = [percentage_returns[code].skew() for code in instrument_codes]

fig, ax = pyplot.subplots()
ax.scatter(skew_list, sharpe_ratios, marker="")
for i, txt in enumerate(instrument_codes):
    ax.annotate(txt, (skew_list[i], sharpe_ratios[i]))


def resampled_SR_estimator_multiple_codes(percentage_returns, code_list, monte_carlo_count=500, avoiding_vol=False):
    """

    :param percentage_returns: dict of returns
    :param code_list: list of str, a subset of percentage_returns.keys
    :param monte_carlo_count: how many times
    :return: list of SR estimtes
    """

    SR_estimate_distribution = []
    for _notUsed in range(monte_carlo_count):
        # randomly choose a code
        # comment in these lines to avoid vol
        if avoiding_vol:
            code = "VIX"
            while code in ["VIX", "V2X"]:
                code = code_list[int(random.uniform(0, len(code_list)))]
        else:
            code = code_list[int(random.uniform(0, len(code_list)))]

        data = percentage_returns[code]
        resample_index = [int(random.uniform(0,len(data))) for _alsoNotUsed in range(len(data))]
        resampled_data = data[resample_index]
        SR_estimate = 16.0*resampled_data.mean()/resampled_data.std()
        SR_estimate_distribution.append(SR_estimate)

    return SR_estimate_distribution

df_SR_distribution_multiple = dict()
df_SR_distribution_multiple['High skew'] = resampled_SR_estimator_multiple_codes(percentage_returns,high_skew_codes,1000, avoiding_vol=True)
df_SR_distribution_multiple['Low skew'] = resampled_SR_estimator_multiple_codes(percentage_returns,low_skew_codes,1000, avoiding_vol=True)

df_SR_distribution_multiple = pd.DataFrame(df_SR_distribution_multiple)
df_SR_distribution_multiple.boxplot()

## check time varying skew results
## Want the returns in the future, versus yesterdays skew

import scipy.stats.stats as stats

all_SR_list = []
all_tstats=[]
all_frequencies = ["7D", "14D", "1M", "3M", "6M", "12M"]

for freqtouse in all_frequencies:
    all_results = []
    for instrument in instrument_codes:
            # we're going to do rolling returns
            perc_returns = percentage_returns[instrument]
            start_date = perc_returns.index[0]
            end_date = perc_returns.index[-1]

            periodstarts = list(pd.date_range(start_date, end_date, freq=freqtouse)) + [
                end_date]

            for periodidx in range(len(periodstarts) - 2):
                # avoid snooping
                p_start = periodstarts[periodidx]+pd.DateOffset(-1)
                p_end = periodstarts[periodidx+1]+pd.DateOffset(-1)
                s_start = periodstarts[periodidx+1]
                s_end = periodstarts[periodidx+2]

                period_skew = perc_returns[p_start:p_end].skew()
                subsequent_return = perc_returns[s_start:s_end].mean()
                subsequent_vol = perc_returns[s_start:s_end].std()
                subsequent_SR = 16*(subsequent_return / subsequent_vol)

                if np.isnan(subsequent_SR) or np.isnan(period_skew):
                    continue
                else:
                    all_results.append([period_skew, subsequent_SR])

    all_results=pd.DataFrame(all_results, columns=['x', 'y'])
    #avg_skew=all_results.x.median()
    avg_skew = 0
    all_results[all_results.x>avg_skew].y.median()
    all_results[all_results.x<avg_skew].y.median()



    #stats.linregress(all_results.x, all_results.y)

    subsequent_sr_distribution = dict()
    subsequent_sr_distribution['High_skew'] = all_results[all_results.x>=avg_skew].y
    subsequent_sr_distribution['Low_skew'] = all_results[all_results.x<avg_skew].y


    subsequent_sr_distribution = pd.DataFrame(subsequent_sr_distribution)
    #subsequent_sr_distribution.boxplot()


    med_SR =subsequent_sr_distribution.median()
    tstat = stats.ttest_ind(subsequent_sr_distribution.High_skew, subsequent_sr_distribution.Low_skew, nan_policy="omit").statistic
    all_SR_list.append(med_SR)
    all_tstats.append(tstat)

all_tstats = pd.Series(all_tstats, index=all_frequencies)
all_tstats.plot()

all_SR_list = pd.DataFrame(all_SR_list, index=all_frequencies)
all_SR_list.plot()


## now demeaned by own asset recent skew
all_SR_list = []
all_tstats=[]
all_frequencies = ["7D", "14D", "1M", "3M", "6M", "12M"]

for freqtouse in all_frequencies:
    all_results = []
    for instrument in instrument_codes:
            # we're going to do rolling returns

            perc_returns = percentage_returns[instrument]
            all_skew = perc_returns.rolling("3650D").skew()

            start_date = perc_returns.index[0]
            end_date = perc_returns.index[-1]

            periodstarts = list(pd.date_range(start_date, end_date, freq=freqtouse)) + [
                end_date]

            for periodidx in range(len(periodstarts) - 2):
                # avoid snooping
                p_start = periodstarts[periodidx]+pd.DateOffset(-1)
                p_end = periodstarts[periodidx+1]+pd.DateOffset(-1)
                s_start = periodstarts[periodidx+1]
                s_end = periodstarts[periodidx+2]

                period_skew = perc_returns[p_start:p_end].skew()
                avg_skew = all_skew[:p_end][-1]
                period_skew = period_skew - avg_skew
                subsequent_return = perc_returns[s_start:s_end].mean()
                subsequent_vol = perc_returns[s_start:s_end].std()
                subsequent_SR = 16*(subsequent_return / subsequent_vol)

                if np.isnan(subsequent_SR) or np.isnan(period_skew):
                    continue
                else:
                    all_results.append([period_skew, subsequent_SR])

    all_results=pd.DataFrame(all_results, columns=['x', 'y'])
    avg_skew=all_results.x.median()
    all_results[all_results.x>avg_skew].y.median()
    all_results[all_results.x<avg_skew].y.median()



    #stats.linregress(all_results.x, all_results.y)

    subsequent_sr_distribution = dict()
    subsequent_sr_distribution['High_skew'] = all_results[all_results.x>=avg_skew].y
    subsequent_sr_distribution['Low_skew'] = all_results[all_results.x<avg_skew].y


    subsequent_sr_distribution = pd.DataFrame(subsequent_sr_distribution)
    #subsequent_sr_distribution.boxplot()


    med_SR =subsequent_sr_distribution.median()
    tstat = stats.ttest_ind(subsequent_sr_distribution.High_skew, subsequent_sr_distribution.Low_skew, nan_policy="omit").statistic
    all_SR_list.append(med_SR)
    all_tstats.append(tstat)

all_tstats = pd.Series(all_tstats, index=all_frequencies)
all_tstats.plot()

all_SR_list = pd.DataFrame(all_SR_list, index=all_frequencies)
all_SR_list.plot()


## now demeaned by cross sectional skew
all_SR_list = []
all_tstats=[]
all_frequencies = ["7D", "14D", "30D", "90D", "180D", "365D"]


for freqtouse in all_frequencies:
    all_results = []
    # relative value skews need averaged

    skew_df = {}
    for instrument in instrument_codes:
        # rolling skew over period
        instrument_skew = percentage_returns[instrument].rolling(freqtouse).skew()
        skew_df[instrument] = instrument_skew

    skew_df_all = pd.DataFrame(skew_df)
    skew_df_median = skew_df_all.median(axis=1)

    for instrument in instrument_codes:
            # we're going to do rolling returns

            perc_returns = percentage_returns[instrument]

            start_date = perc_returns.index[0]
            end_date = perc_returns.index[-1]

            periodstarts = list(pd.date_range(start_date, end_date, freq=freqtouse)) + [
                end_date]

            for periodidx in range(len(periodstarts) - 2):
                # avoid snooping
                p_start = periodstarts[periodidx]+pd.DateOffset(-1)
                p_end = periodstarts[periodidx+1]+pd.DateOffset(-1)
                s_start = periodstarts[periodidx+1]
                s_end = periodstarts[periodidx+2]

                period_skew = perc_returns[p_start:p_end].skew()
                avg_skew = skew_df_median[:p_end][-1]
                period_skew = period_skew - avg_skew
                subsequent_return = perc_returns[s_start:s_end].mean()
                subsequent_vol = perc_returns[s_start:s_end].std()
                subsequent_SR = 16*(subsequent_return / subsequent_vol)

                if np.isnan(subsequent_SR) or np.isnan(period_skew):
                    continue
                else:
                    all_results.append([period_skew, subsequent_SR])

    all_results=pd.DataFrame(all_results, columns=['x', 'y'])
    avg_skew=all_results.x.median()
    all_results[all_results.x>avg_skew].y.median()
    all_results[all_results.x<avg_skew].y.median()



    #stats.linregress(all_results.x, all_results.y)

    subsequent_sr_distribution = dict()
    subsequent_sr_distribution['High_skew'] = all_results[all_results.x>=avg_skew].y
    subsequent_sr_distribution['Low_skew'] = all_results[all_results.x<avg_skew].y


    subsequent_sr_distribution = pd.DataFrame(subsequent_sr_distribution)
    #subsequent_sr_distribution.boxplot()


    med_SR =subsequent_sr_distribution.median()
    tstat = stats.ttest_ind(subsequent_sr_distribution.High_skew, subsequent_sr_distribution.Low_skew, nan_policy="omit").statistic
    all_SR_list.append(med_SR)
    all_tstats.append(tstat)

all_tstats = pd.Series(all_tstats, index=all_frequencies)
all_tstats.plot()

all_SR_list = pd.DataFrame(all_SR_list, index=all_frequencies)
all_SR_list.plot()




all_SR_list = []
all_tstats=[]
all_frequencies = ["7D", "14D", "30D", "90D", "180D", "365D"]
asset_classes = list(system.data.get_instrument_asset_classes().unique())

for freqtouse in all_frequencies:
    all_results = []
    # relative value skews need averaged

    skew_df_median_by_asset_class = {}
    for asset in asset_classes:
        skew_df = {}
        for instrument in system.data.all_instruments_in_asset_class(asset):
            # rolling skew over period
            instrument_skew = percentage_returns[instrument].rolling(freqtouse).skew()
            skew_df[instrument] = instrument_skew

        skew_df_all = pd.DataFrame(skew_df)
        skew_df_median = skew_df_all.median(axis=1)
        # will happen if only one asset class
        skew_df_median[skew_df_median==0] = np.nan

        skew_df_median_by_asset_class[asset] = skew_df_median

    for instrument in instrument_codes:
            # we're going to do rolling returns
            asset_class = system.data.asset_class_for_instrument(instrument)

            perc_returns = percentage_returns[instrument]

            start_date = perc_returns.index[0]
            end_date = perc_returns.index[-1]

            periodstarts = list(pd.date_range(start_date, end_date, freq=freqtouse)) + [
                end_date]

            for periodidx in range(len(periodstarts) - 2):
                # avoid snooping
                p_start = periodstarts[periodidx]+pd.DateOffset(-1)
                p_end = periodstarts[periodidx+1]+pd.DateOffset(-1)
                s_start = periodstarts[periodidx+1]
                s_end = periodstarts[periodidx+2]

                period_skew = perc_returns[p_start:p_end].skew()

                avg_skew = skew_df_median_by_asset_class[asset_class][:p_end][-1]
                period_skew = period_skew - avg_skew
                subsequent_return = perc_returns[s_start:s_end].mean()
                subsequent_vol = perc_returns[s_start:s_end].std()
                subsequent_SR = 16*(subsequent_return / subsequent_vol)

                if np.isnan(subsequent_SR) or np.isnan(period_skew):
                    continue
                else:
                    all_results.append([period_skew, subsequent_SR])

    all_results=pd.DataFrame(all_results, columns=['x', 'y'])
    avg_skew=all_results.x.median()
    all_results[all_results.x>avg_skew].y.median()
    all_results[all_results.x<avg_skew].y.median()



    #stats.linregress(all_results.x, all_results.y)

    subsequent_sr_distribution = dict()
    subsequent_sr_distribution['High_skew'] = all_results[all_results.x>=avg_skew].y
    subsequent_sr_distribution['Low_skew'] = all_results[all_results.x<avg_skew].y


    subsequent_sr_distribution = pd.DataFrame(subsequent_sr_distribution)
    #subsequent_sr_distribution.boxplot()


    med_SR =subsequent_sr_distribution.median()
    tstat = stats.ttest_ind(subsequent_sr_distribution.High_skew, subsequent_sr_distribution.Low_skew, nan_policy="omit").statistic
    all_SR_list.append(med_SR)
    all_tstats.append(tstat)

all_tstats = pd.Series(all_tstats, index=all_frequencies)
all_tstats.plot()

all_SR_list = pd.DataFrame(all_SR_list, index=all_frequencies)
all_SR_list.plot()


