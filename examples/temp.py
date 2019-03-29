import matplotlib.pyplot as plt
import pandas as pd
import scipy.stats as stats
import numpy as np

from systems.provided.futures_chapter15.estimatedsystem import *
system = futures_system()

del(system.config.instruments) # so we can get results for everything

# generate all pandl curves
instruments = system.get_instrument_list()
trading_rules = ['ewmac2_8', 'ewmac4_16','ewmac8_32','ewmac16_64', 'ewmac32_128','ewmac64_256']
rule_id_dict = dict(ewmac2_8 = 2, ewmac16_64=16, ewmac64_256=64, ewmac4_16=4, ewmac8_32=8, ewmac32_128=32)
periods = ['daily', 'weekly', 'monthly', 'annual']


## Want to check the relationship between recent skew, and future risk adjusted return
all_results = []
for instrument in instruments:
        # we're going to do rolling returns
        perc_returns = system.rawdata.daily_returns(instrument) / system.rawdata.daily_denominator_price(instrument)
        start_date = perc_returns.index[0]
        end_date = perc_returns.index[-1]

        periodstarts = list(pd.date_range(start_date, end_date, freq="3M")) + [
            end_date]

        for periodidx in range(len(periodstarts) - 2):
            p_start = periodstarts[periodidx]
            p_end = periodstarts[periodidx+1]
            s_end = periodstarts[periodidx+2]

            period_skew = perc_returns[p_start:p_end].skew()
            subsequent_return = perc_returns[p_end:s_end].mean()
            subsequent_vol = perc_returns[p_end:s_end].std()
            subsequent_SR = 16*(subsequent_return / subsequent_vol)

            all_results.append([period_skew, subsequent_SR])

all_results=pd.DataFrame(all_results, columns=['x', 'y'])
all_results[all_results.x>0].y.median()
all_results[all_results.x<0].y.median()


varx=all_results.x
vary=all_results.y
mask = ~np.isnan(varx) & ~np.isnan(vary)

stats.linregress(varx[mask], vary[mask])


## check trend following returns, skew over different periods
all_results = []
for instrument in instruments:
    for rule in trading_rules:
        pandl = system.accounts.pandl_for_instrument_forecast(instrument, rule)
        rule_id = rule_id_dict[rule]
        # we're going to do rolling returns
        start_date = pandl.index[0]
        end_date = pandl.index[-1]

        yearstarts = list(pd.date_range(start_date, end_date, freq="12M")) + [
            end_date]

        for period in periods:
            period_pandl = getattr(pandl, period)

            if period == "annual":
                period_skew = period_pandl.skew()
                results_label = [instrument, rule_id,  0, period]
                all_results.append(results_label + [period_skew])
            else:
                # other time periods, we look at multiple examples
                for yearidx in range(len(yearstarts) - 1):
                    period_start = yearstarts[yearidx]
                    period_end = yearstarts[yearidx+1]
                    sub_period_pandl = period_pandl[period_start:period_end]

                period_skew = sub_period_pandl.skew()
                results_label = [instrument, rule_id, yearidx, period]
                all_results.append(results_label+[period_skew])

all_results = pd.DataFrame(all_results, columns=['instrument', 'rule', 'idx', 'period', 'skew'])

# plot results
# daily etc
all_results[(all_results['period']=='daily')].plot.scatter('rule', 'skew')
all_results[(all_results['period']=='daily') & (all_results['rule']==2)]['skew'].median()
grouped = all_results[['rule', 'period', 'skew']].groupby(['rule', 'period'], as_index=False).median()

rule_id_list = list(rule_id_dict.values())
rule_id_list.sort()

median_results = [[all_results[
                      (all_results['period']==period) & (all_results['rule']==rule_id)
                  ]['skew'].median() for rule_id in rule_id_list] for period in periods]
median_results = pd.DataFrame(median_results)

median_results.columns = trading_rules
median_results.index = periods
median_results.plot()
ax = plt.gca()
ax.set_xticklabels(periods)

# check to see if trend following rules are long skew,
forecasts = []
skews_before = []
skews_after = []
rules = []
for instrument in instruments:
    for rule in trading_rules:
        rule_id = rule_id_dict[rule]

        forecast = system.forecastScaleCap.get_scaled_forecast(instrument, rule).ffill()
        perc_returns = system.rawdata.daily_returns(instrument) / system.rawdata.daily_denominator_price(instrument)
        start_date = perc_returns.index[0]
        end_date = perc_returns.index[-1]

        periodstarts = list(pd.date_range(start_date, end_date, freq="1M")) + [
            end_date]

        for periodidx in range(len(periodstarts) - 2):
            p_start = periodstarts[periodidx]
            p_end = periodstarts[periodidx+1]
            s_end = periodstarts[periodidx+2]
            pre_period_skew = perc_returns[p_start:p_end].skew()
            post_period_skew = perc_returns[p_end:s_end].skew()
            forecast_value = forecast[p_end-pd.DateOffset(days=-2):p_end+pd.DateOffset(days=+2)].mean()

            if not np.isnan(forecast_value):
                forecasts.append(forecast_value)
                rules.append(rule_id)
                skews_before.append(pre_period_skew)
                skews_after.append(post_period_skew)

results = pd.DataFrame(np.array([rules, forecasts, skews_before, skews_after]).transpose(), columns=['rule','forecast','pre_skew', 'post_skew'])

median_results=[]
for comparator in ['lesser','greater']:
    c_results = []
    for rule_id in rule_id_list:
        if comparator=="greater":
            sub_results = results[(results.rule==rule_id) & (results.forecast>0)].post_skew.median()
        else:
            sub_results = results[(results.rule == rule_id) & (results.forecast < 0)].post_skew.median()
        c_results.append(sub_results)
    median_results.append(c_results)

median_results = pd.DataFrame(median_results)

median_results.columns = trading_rules
median_results.index = ['short', 'long']
median_results.plot()

median_results=[]
for comparator in ['lesser','greater']:
    c_results = []
    for rule_id in rule_id_list:
        if comparator=="greater":
            sub_results = results[(results.rule==rule_id) & (results.forecast>0)].pre_skew.median()
        else:
            sub_results = results[(results.rule == rule_id) & (results.forecast < 0)].pre_skew.median()
        c_results.append(sub_results)
    median_results.append(c_results)

median_results = pd.DataFrame(median_results)

median_results.columns = trading_rules
median_results.index = ['short', 'long']
median_results.plot()
