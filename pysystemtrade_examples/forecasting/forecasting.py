from matplotlib.pyplot import plot, scatter
from sysdata.csvdata import csvFuturesData
import pandas as pd
import numpy as np
from scipy.stats import linregress
from syscore.algos import robust_vol_calc

from syscore.dateutils import  fit_dates_object
from syscore.genutils import progressBar

code="US10"


data_object=csvFuturesData()
prices=data_object[code]
perc=(prices - prices.shift(1))/data_object.get_instrument_raw_carry_data(code)['PRICE']
perc[abs(perc)>0.03]=np.nan

def get_expost_data(perc):
    fitting_dates = generate_fitting_dates(perc, "rolling") ## only using annual dates rolling doesn't matter
    expost_data = [perc[fit_date.period_start:fit_date.period_end] for fit_date in fitting_dates[1:]]

    return expost_data



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

def calc_historic_mean_distr_annual(perc, fit_date):
    data=perc[fit_date.fit_start:fit_date.fit_end]
    avg = data.mean()
    std = data.std()

    conf_interval_mult = (std**2 / len(data))**.5
    conf_interval_days = [avg - 1.96 * conf_interval_mult, avg + 1.96 * conf_interval_mult]
    conf_interval = np.array(conf_interval_days)*250

    return list(conf_interval)



def single_bootstrap_from_data(data):
    n = len(data)
    bootstraps = [int(np.random.uniform(high=n)) for not_used in range(n)]
    bs_data=[data[bsnumber] for bsnumber in bootstraps]
    return bs_data

def gen_bootstraps_from_data(data, monte_carlo=500):

    all_bs = [single_bootstrap_from_data(data) for not_used in range(monte_carlo)]

    return all_bs


def calc_historic_SR_distr_annual(perc, fit_date):
    data=perc[fit_date.fit_start:fit_date.fit_end]
    SR = data.mean() / data.std()
    SR_std = ((1+.5*SR**2)/len(data))**.5

    conf_interval = (16*(SR - 2*SR_std), 16*(SR + 2*SR_std))

    return conf_interval


def calc_historic_std_distr_annual(perc, fit_date):
    data=perc[fit_date.fit_start:fit_date.fit_end]

    ## bootstrap
    all_bs  = gen_bootstraps_from_data(data)
    all_bs_std = [np.nanstd(bs_data)*16 for bs_data in all_bs]
    conf_interval = [np.percentile(all_bs_std,2.5), np.percentile(all_bs_std, 97.5)]

    return list(conf_interval)

def calc_historic_distr_annual(perc, fit_date):
    data = perc[fit_date.fit_start:fit_date.fit_end]

    data_mean = data.mean()
    data_std = data.std()

    conf_interval = (data_mean - 1.96*data_std, data_mean + 1.96*data_std)

    return conf_interval


def ewmav(x, span=35):
    vol = x.ewm(adjust=True, span=span, min_periods=5).std()
    return vol[-1]

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



expost_data = get_expost_data(perc)


list_of_confidence = calc_historic_confidence(perc, function_to_use=calc_historic_mean_distr_annual)
expost_dates = list_of_confidence.index

expost_means = [period_data.mean()*250 for period_data in expost_data]
expost_means = pd.DataFrame(expost_means, expost_dates)


datatoplot = pd.concat([list_of_confidence, expost_means], axis=1)
datatoplot.columns=["lower","upper","actual"]


list_of_confidence = calc_historic_confidence(perc, function_to_use=calc_historic_std_distr_annual)
expost_std = [period_data.std()*16 for period_data in expost_data]
expost_std = pd.DataFrame(expost_std, expost_dates)
datatoplot = pd.concat([list_of_confidence, expost_std], axis=1)
datatoplot.columns=["lower","upper","actual"]

list_of_confidence = calc_historic_confidence(perc, function_to_use=calc_historic_SR_distr_annual)
expost_ssr = [16*period_data.mean()/period_data.std() for period_data in expost_data]
expost_ssr = pd.DataFrame(expost_ssr, expost_dates)
datatoplot = pd.concat([list_of_confidence, expost_ssr], axis=1)
datatoplot.columns=["lower","upper","actual"]

entire_distribution = calc_historic_confidence(perc, function_to_use=calc_historic_distr_annual)
entire_distribution.plot()
perc.plot()

def sr_func(data):
    return data.mean()/data.std()

data=perc
period="10B"
rollperiods=1 ## set to very large number if using exp std
expost_function_to_use=np.nanstd
exante_function_to_use=np.nanstd
multiplier_to_apply=16.0
fitting_dates=generate_fitting_dates(perc, "rolling", period=period, rollperiods=rollperiods)
ex_ante_value_list=[]
ex_post_value_list=[]

for fit_date in fitting_dates[1:]:
    ex_ante_data=data[fit_date.fit_start:fit_date.fit_end]
    ex_ante_value = exante_function_to_use(ex_ante_data)*multiplier_to_apply

    ex_post_data=data[fit_date.period_start:fit_date.period_end]
    ex_post_value = expost_function_to_use(ex_post_data)*multiplier_to_apply

    if not (np.isnan(ex_ante_value) or np.isnan(ex_post_value)):

        ex_post_value_list.append(ex_post_value)
        ex_ante_value_list.append(ex_ante_value)

scatter(ex_ante_value_list, ex_post_value_list)

print(linregress(ex_ante_value_list, ex_post_value_list))

def calc_ewmac_forecast(price, Lfast=64, Lslow=256):
    """
    Calculate the ewmac trading fule forecast, given a price and EWMA speeds
    Lfast, Lslow and vol_lookback

    """
    # price: This is the stitched price series
    # We can't use the price of the contract we're trading, or the volatility
    # will be jumpy
    # And we'll miss out on the rolldown. See
    # http://qoppac.blogspot.co.uk/2015/05/systems-building-futures-rolling.html

    price = price.resample("1B").last()

    if Lslow is None:
        Lslow = 4 * Lfast

    # We don't need to calculate the decay parameter, just use the span
    # directly
    fast_ewma = price.ewm(span=Lfast).mean()
    slow_ewma = price.ewm(span=Lslow).mean()
    raw_ewmac = fast_ewma - slow_ewma

    vol = robust_vol_calc(price.diff())
    return raw_ewmac / vol

price = data_object.daily_prices(code)
ewmac = calc_ewmac_forecast(price, 16, 64)



data=perc
period="1M"
rollperiods=1 ## set to very large number if using exp std
exante_function_to_use=sr_func
multiplier_to_apply=16.0
fitting_dates=generate_fitting_dates(perc, "rolling", period=period, rollperiods=rollperiods)
ex_ante_value_list=[]
ex_post_value_list=[]


for fit_date in fitting_dates[1:]:
    ex_ante_value = ewmac[:fit_date.fit_end][-1]

    ex_post_data=data[fit_date.period_start:fit_date.period_end]
    ex_post_value = expost_function_to_use(ex_post_data)*multiplier_to_apply

    if not (np.isnan(ex_ante_value) or np.isnan(ex_post_value)):

        ex_post_value_list.append(ex_post_value)
        ex_ante_value_list.append(ex_ante_value)

scatter(ex_ante_value_list, ex_post_value_list)

print(linregress(ex_ante_value_list, ex_post_value_list))

from systems.provided.futures_chapter15.basesystem import futures_system