from copy import copy

import numpy as np
import pandas as pd

from syscore.dateutils import ROOT_BDAYS_INYEAR, BUSINESS_DAYS_IN_YEAR
from syscore.objects import resolve_function
from syscore.constants import arg_not_supplied
from syscore.pandas.frequency import resample_prices_to_business_day_index
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.prices import (
    get_current_price_of_instrument,
    get_price_series,
    get_current_price_series,
)
from sysproduction.data.capital import capital_for_strategy
from sysquant.estimators.correlations import correlationEstimate
from sysquant.estimators.covariance import (
    covarianceEstimate,
    covariance_from_stdev_and_correlation,
)
from sysquant.estimators.stdev_estimator import stdevEstimates
from sysquant.fitting_dates import IN_SAMPLE


def get_covariance_matrix_for_instrument_returns(
    data,
    list_of_instruments: list,
    passed_correlation_estimation_parameters: dict = arg_not_supplied,
) -> covarianceEstimate:
    corr_matrix = get_correlation_matrix_for_instrument_returns(
        data,
        list_of_instruments,
        passed_correlation_estimation_parameters=passed_correlation_estimation_parameters,
    )

    stdev_estimate = get_annualised_stdev_perc_of_instruments(
        data, instrument_list=list_of_instruments
    )
    covariance = covariance_from_stdev_and_correlation(
        stdev_estimate=stdev_estimate, correlation_estimate=corr_matrix
    )

    return covariance


def get_correlation_matrix_for_instrument_returns(
    data,
    list_of_instruments: list,
    passed_correlation_estimation_parameters: dict = arg_not_supplied,
) -> correlationEstimate:
    list_of_correlations = _replicate_creation_of_correlation_list_in_sim(
        data,
        list_of_instruments,
        passed_correlation_estimation_parameters=passed_correlation_estimation_parameters,
    )

    correlation_matrix = list_of_correlations.most_recent_correlation_before_date()

    return correlation_matrix


def _replicate_creation_of_correlation_list_in_sim(
    data,
    list_of_instruments: list,
    passed_correlation_estimation_parameters: dict = arg_not_supplied,
):
    ## double coding but too complex to do differently

    returns_as_pd = get_perc_returns_across_instruments(data, list_of_instruments)
    corr_func, correlation_estimation_parameters = get_corr_params_and_func(
        data,
        passed_correlation_estimation_parameters=passed_correlation_estimation_parameters,
    )

    return corr_func(returns_as_pd, **correlation_estimation_parameters)


def get_annualised_stdev_perc_of_instruments(data, instrument_list) -> stdevEstimates:
    stdev_estimate = stdevEstimates(
        [
            (
                instrument_code,
                get_current_annualised_perc_stdev_for_instrument(data, instrument_code),
            )
            for instrument_code in instrument_list
        ]
    )

    return stdev_estimate


def get_perc_returns_across_instruments(data, instrument_list: list) -> pd.DataFrame:
    perc_returns = dict(
        [
            (instrument_code, get_daily_perc_returns_for_risk(data, instrument_code))
            for instrument_code in instrument_list
        ]
    )
    price_df = pd.DataFrame(perc_returns)

    return price_df


def get_current_annualised_perc_stdev_for_instrument(data, instrument_code) -> float:
    current_daily_vol = get_current_daily_perc_stdev_for_instrument(
        data, instrument_code
    )
    return current_daily_vol * ROOT_BDAYS_INYEAR


def get_current_daily_perc_stdev_for_instrument(data, instrument_code) -> float:
    ts_of_perc_stdev = get_daily_ts_stdev_perc_of_prices(data, instrument_code)
    if len(ts_of_perc_stdev) == 0:
        last_daily_vol = np.nan
    else:
        last_daily_vol = ts_of_perc_stdev.ffill().values[-1]

    return last_daily_vol


def get_daily_ts_stdev_perc_of_prices(data, instrument_code: str) -> pd.Series:
    ## 100 scaled
    denom_price = get_daily_current_price_series_for_risk(data, instrument_code)
    return_vol = get_daily_ts_stdev_of_prices(data, instrument_code)
    (denom_price, return_vol) = denom_price.align(return_vol, join="right")
    perc_vol = return_vol / denom_price.ffill()

    return perc_vol


def get_corr_params_and_func(
    data, passed_correlation_estimation_parameters: dict = arg_not_supplied
) -> tuple:
    if passed_correlation_estimation_parameters is arg_not_supplied:
        config = data.config
        corr_params = config.get_element("instrument_returns_correlation")
    else:
        corr_params = passed_correlation_estimation_parameters

    corr_params = copy(corr_params)
    corr_params["date_method"] = IN_SAMPLE
    corr_func = resolve_function(corr_params.pop("func"))

    return corr_func, corr_params


def get_perc_of_strategy_capital_for_instrument_per_contract(
    data, strategy_name, instrument_code
):
    capital_base_fx = capital_for_strategy(data, strategy_name)
    exposure_per_contract = get_exposure_per_contract_base_currency(
        data, instrument_code
    )

    return exposure_per_contract / capital_base_fx


def get_current_ann_stdev_of_prices(data, instrument_code):
    try:
        current_stdev_ann_price_units = get_ann_ts_stdev_of_prices(
            data=data, instrument_code=instrument_code
        ).iloc[-1]
    except:
        ## can happen for brand new instruments not properly loaded
        return np.nan

    return current_stdev_ann_price_units


def get_ann_ts_stdev_of_prices(data, instrument_code):
    stdev_ann_price_units = get_daily_ts_stdev_of_prices(
        data=data, instrument_code=instrument_code
    )

    return stdev_ann_price_units * ROOT_BDAYS_INYEAR


def get_daily_ts_stdev_of_prices(data, instrument_code):
    dailyreturns = get_daily_returns_for_risk(data, instrument_code)
    volconfig = copy(vol_config(data))

    # volconfig contains 'func' and some other arguments
    # we turn func which could be a string into a function, and then
    # call it with the other args

    volfunction = resolve_function(volconfig.pop("func"))
    vol = volfunction(dailyreturns, **volconfig)

    return vol


def vol_config(data) -> dict:
    config = data.config
    vol_config = config.get_element("volatility_calculation")
    return vol_config


def get_exposure_per_contract_base_currency(data, instrument_code):
    point_size_base_currency = get_base_currency_point_size_per_contract(
        data, instrument_code
    )
    price = get_current_price_of_instrument(data, instrument_code)

    return point_size_base_currency * price


def get_base_currency_point_size_per_contract(data, instrument_code):
    diag_instruments = diagInstruments(data)
    point_size_base_currency = diag_instruments.get_point_size_base_currency(
        instrument_code
    )

    return point_size_base_currency


def get_daily_perc_returns_for_risk(data, instrument_code):
    daily_returns = get_daily_returns_for_risk(data, instrument_code)
    daily_prices = get_daily_current_price_series_for_risk(data, instrument_code)

    return daily_returns / daily_prices


def get_daily_returns_for_risk(data, instrument_code):
    daily_prices = get_daily_price_series_for_risk(data, instrument_code)
    daily_returns = daily_prices.diff()

    return daily_returns


def get_daily_price_series_for_risk(data, instrument_code):
    price_series = get_price_series(data, instrument_code)
    if len(price_series) == 0:
        return price_series

    daily_prices = resample_prices_to_business_day_index(price_series)

    return daily_prices[-DAILY_RISK_CALC_LOOKBACK:]


def get_daily_current_price_series_for_risk(data, instrument_code):
    price_series = get_current_price_series(data, instrument_code)
    if len(price_series) == 0:
        return price_series

    daily_prices = price_series.resample("1B").last()

    return daily_prices[-DAILY_RISK_CALC_LOOKBACK:]


DAILY_RISK_CALC_LOOKBACK = int(BUSINESS_DAYS_IN_YEAR * 2)
