from matplotlib.pyplot import plot, scatter
from sysdata.csvdata import csvFuturesData
import pandas as pd
import numpy as np
from scipy.stats import linregress
from syscore.algos import robust_vol_calc

from syscore.dateutils import  fit_dates_object
from syscore.genutils import progressBar

codes=["US10", "US5", "SP500"]


data_object=csvFuturesData()
prices=[data_object[code] for code in codes]
prices=pd.concat(prices, axis=1)
prices.columns = codes
prices = prices[pd.datetime(1998,9,10):]

underlying = [data_object.get_instrument_raw_carry_data(code)['PRICE'] for code in codes]
underlying=pd.concat(underlying, axis=1)
underlying.columns = codes
underlying = underlying[pd.datetime(1998,9,10):]

perc=(prices - prices.shift(1))/underlying.shift(1)
perc['US10'][abs(perc['US10'])>0.03]=np.nan

def get_expost_data(perc):
    fitting_dates = generate_fitting_dates(perc, "rolling") ## only using annual dates rolling doesn't matter
    expost_data = [perc[fit_date.period_start:fit_date.period_end] for fit_date in fitting_dates[1:]]

    return expost_data


def generate_fitting_dates(data, date_method, period="12M",rollperiods=20):
    """
    generate a list 4 tuples, one element for each period in the data
    each tuple contains [fit_start, fit_end, period_start, period_end] datetime objects
    the last period will be a 'stub' if we haven't got an exact number of years

    date_method can be one of 'in_sample', 'expanding', 'rolling'

    if 'rolling' then use rollperiods variable
    """

    if date_method not in ["in_sample", "rolling", "expanding"]:
        raise Exception(
            "don't recognise date_method %s should be one of in_sample, expanding, rolling"
            % date_method)

    if isinstance(data, list):
        start_date = min([dataitem.index[0] for dataitem in data])
        end_date = max([dataitem.index[-1] for dataitem in data])
    else:
        start_date = data.index[0]
        end_date = data.index[-1]

    # now generate the dates we use to fit
    if date_method == "in_sample":
        # single period
        return [fit_dates_object(start_date, end_date, start_date, end_date)]

    # generate list of dates, one period apart, including the final date
    period_starts = list(pd.date_range(start_date, end_date, freq=period)) + [
        end_date
    ]

    # loop through each period
    periods = []
    for tidx in range(len(period_starts))[1:-1]:
        # these are the dates we test in
        period_start = period_starts[tidx]
        period_end = period_starts[tidx + 1]

        # now generate the dates we use to fit
        if date_method == "expanding":
            fit_start = start_date
        elif date_method == "rolling":
            yearidx_to_use = max(0, tidx - rollperiods)
            fit_start = period_starts[yearidx_to_use]
        else:
            raise Exception(
                "don't recognise date_method %s should be one of in_sample, expanding, rolling"
                % date_method)

        if date_method in ['rolling', 'expanding']:
            fit_end = period_start
        else:
            raise Exception("don't recognise date_method %s " % date_method)

        periods.append(
            fit_dates_object(fit_start, fit_end, period_start, period_end))

    if date_method in ['rolling', 'expanding']:
        # add on a dummy date for the first year, when we have no data
        periods = [
            fit_dates_object(
                start_date,
                start_date,
                start_date,
                period_starts[1],
                no_data=True)
        ] + periods

    return periods



def calc_historic_confidence(perc, function_to_use, rollperiods=250):
    fitting_dates=generate_fitting_dates(perc, "rolling", rollperiods=rollperiods)

    list_of_confidence=[]
    thing=progressBar(len(fitting_dates)-1)
    for fit_date in fitting_dates[1:]:
        list_of_confidence.append(function_to_use(perc, fit_date))
        thing.iterate()
    thing.finished()


    list_of_confidence = pd.DataFrame(list_of_confidence, index=[fit_date.fit_end for fit_date in fitting_dates[1:]])
    list_of_confidence.columns = ["lower", "upper"]

    return list_of_confidence

def single_bootstrap_from_data(data):
    n = len(data)
    bootstraps = [int(np.random.uniform(high=n)) for not_used in range(n)]
    bs_data=[data.iloc[bsnumber] for bsnumber in bootstraps]
    return bs_data

def gen_bootstraps_from_data(data, monte_carlo=100):

    all_bs = [single_bootstrap_from_data(data) for not_used in range(monte_carlo)]

    return all_bs


def calc_historic_corr_distr_annual__us10_us5(perc, fit_date):
    data=perc[fit_date.fit_start:fit_date.fit_end]

    ## bootstrap
    all_bs  = gen_bootstraps_from_data(data)

    all_bs_corr = [pd.concat(bs_item, axis=1).transpose().corr() for bs_item in all_bs]
    all_bs_corr = [bs_corr_item.values[0][1] for bs_corr_item in all_bs_corr]

    conf_interval = [np.percentile(all_bs_corr,2.5), np.percentile(all_bs_corr, 97.5)]

    return list(conf_interval)

def calc_historic_corr_distr_annual__us10_sp500(perc, fit_date=None):

    data=perc[fit_date.fit_start:fit_date.fit_end]

    ## bootstrap
    all_bs  = gen_bootstraps_from_data(data)

    all_bs_corr = [pd.concat(bs_item, axis=1).transpose().corr() for bs_item in all_bs]
    all_bs_corr = [bs_corr_item.values[0][2] for bs_corr_item in all_bs_corr]

    conf_interval = [np.percentile(all_bs_corr,2.5), np.percentile(all_bs_corr, 97.5)]

    return list(conf_interval)

expost_data = get_expost_data(perc)


list_of_confidence = calc_historic_confidence(perc, function_to_use=calc_historic_corr_distr_annual__us10_us5)
expost_dates = list_of_confidence.index
expost_corr = [period_data.corr().values[0][1] for period_data in expost_data]
expost_corr = pd.DataFrame(expost_corr, expost_dates)
datatoplot = pd.concat([list_of_confidence, expost_corr], axis=1)
datatoplot.columns=["lower","upper","actual"]

list_of_confidence2 = calc_historic_confidence(perc, function_to_use=calc_historic_corr_distr_annual__us10_sp500)
expost_corr = [period_data.corr().values[0][2] for period_data in expost_data]
expost_corr = pd.DataFrame(expost_corr, expost_dates)
datatoplot = pd.concat([list_of_confidence2, expost_corr], axis=1)
datatoplot.columns=["lower","upper","actual"]

def corr1(period_data):
    return period_data.corr().values[0][1]

def corr2(period_data):
    return period_data.corr().values[0][2]


data=perc
period="5D"
rollperiods=1 ## set to very large number if using exp std
expost_function_to_use=corr2
exante_function_to_use=corr2
fitting_dates=generate_fitting_dates(perc, "rolling", period=period, rollperiods=rollperiods)
ex_ante_value_list=[]
ex_post_value_list=[]

for fit_date in fitting_dates[1:]:
    ex_ante_data=data[fit_date.fit_start:fit_date.fit_end]
    ex_ante_value = exante_function_to_use(ex_ante_data)

    ex_post_data=data[fit_date.period_start:fit_date.period_end]
    ex_post_value = expost_function_to_use(ex_post_data)

    if not (np.isnan(ex_ante_value) or np.isnan(ex_post_value)):

        ex_post_value_list.append(ex_post_value)
        ex_ante_value_list.append(ex_ante_value)

scatter(ex_ante_value_list, ex_post_value_list)

print(linregress(ex_ante_value_list, ex_post_value_list))
