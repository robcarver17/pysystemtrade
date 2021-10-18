import numpy as np
import pandas as pd

from syscore.dateutils import ROOT_BDAYS_INYEAR, BUSINESS_DAYS_IN_YEAR
from syscore.objects import missing_data

from sysobjects.production.tradeable_object import instrumentStrategy

from sysquant.estimators.covariance import covarianceEstimate, covariance_from_stdev_and_correlation
from sysquant.estimators.correlations import correlationEstimate
from sysquant.estimators.exponential_correlation import exponentialCorrelation
from sysquant.estimators.stdev_estimator import stdevEstimates
from sysquant.optimisation.weights import portfolioWeights

from sysproduction.data.capital import dataCapital
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.positions import diagPositions
from sysproduction.data.prices import diagPrices

from sysquant.optimisation.shared import sigma_from_corr_and_std

## FIX ME SOME DUPLICATE CODE HERE AND DIFFERENT METHODS SHOULD BE MAKING MORE OF SYSQUANT

def get_annualised_perc_of_capital_risk_of_positions_held_for_instruments_across_strategies(data, instrument_code):
    capital_base_fx = total_capital(data)
    base_currency_risk = get_base_currency_risk_held_for_instrument_across_strategies(data, instrument_code)

    perc_of_capital_risk = base_currency_risk / capital_base_fx

    return perc_of_capital_risk


def get_portfolio_risk_for_strategy(data, strategy_name):

    weights = get_perc_of_capital_position_size_across_instruments_for_strategy(data,
                                                                                strategy_name)
    instrument_list = list(weights.keys())
    cmatrix = get_correlation_matrix(data, instrument_list)
    std_dev = get_annualised_stdev_for_instruments(data, instrument_list)

    risk = get_annualised_risk_given_inputs(std_dev, cmatrix, weights)

    return risk

def get_perc_of_capital_position_size_across_instruments_for_strategy(
        data,
        strategy_name: str) -> portfolioWeights:

    instrument_list = get_instruments_with_positions(data, strategy_name)
    weights = portfolioWeights(
        [(
            instrument_code,
        get_perc_of_capital_position_size_for_instrument(data, strategy_name, instrument_code)
          )
        for instrument_code in instrument_list]
    )

    return weights

def get_covariance_matrix(data, list_of_instruments: list) -> covarianceEstimate:
    corr_matrix = get_correlation_matrix(data,
                                         instrument_list=list_of_instruments)
    stdev_estimate = get_list_of_annualised_stdev_of_instruments_as_estimate(data,
                                                                             instrument_list=list_of_instruments)
    covariance = covariance_from_stdev_and_correlation(stdev_estimate=stdev_estimate,
                                                      correlation_estimate=corr_matrix)

    return covariance

def get_annualised_risk_given_inputs(
        std_dev: stdevEstimates,
        cmatrix: correlationEstimate,
        weights: portfolioWeights) -> float:

    weights_as_np = weights.as_np()
    std_dev_as_np = std_dev.as_np()
    cmatrix_as_np = cmatrix.as_np()

    std_dev_as_np, cmatrix_as_np, weights_as_np = clean_values(std_dev_as_np,
                                                               cmatrix_as_np,
                                                               weights_as_np)
    sigma = sigma_from_corr_and_std(std_dev_as_np, cmatrix_as_np)

    portfolio_variance = weights_as_np.dot(sigma).dot(weights_as_np.transpose())
    portfolio_std = portfolio_variance**.5

    return portfolio_std


def clean_values(std_dev: np.array,
                 cmatrix: np.array,
                 weights: np.array):

    cmatrix[np.isnan(cmatrix)] = 1.0
    weights[np.isnan(weights)] = 0.0
    std_dev[np.isnan(std_dev)] = 100.0

    return std_dev, cmatrix, weights


def get_correlation_matrix_all_instruments(data) -> correlationEstimate:
    instrument_list = get_instruments_with_positions_all_strategies(data)
    cmatrix = get_correlation_matrix(data, instrument_list)
    cmatrix = cmatrix.ordered_correlation_matrix()

    return cmatrix

def get_correlation_matrix(data, instrument_list: list,
                           span_days: int = 375) -> correlationEstimate:
    perc_returns = dict([(instrument_code, get_daily_perc_returns(data, instrument_code))
                for instrument_code in instrument_list])
    price_df = pd.DataFrame(perc_returns)

    price_df = price_df[-span_days:]

    exp_correlation_estimator = exponentialCorrelation(price_df,ew_lookback=span_days, floor_at_zero=False)
    last_correlation = exp_correlation_estimator.get_estimate_for_fitperiod_with_data()

    return last_correlation

def get_list_of_annualised_stdev_of_instruments_as_estimate(data, instrument_list) -> stdevEstimates:
    stdev_estimate = stdevEstimates([
        (instrument_code,
         get_current_annualised_perc_stdev_for_instrument(data, instrument_code))

        for instrument_code in instrument_list
    ])

    return stdev_estimate


def get_annualised_stdev_for_instruments(data,
                                         instrument_list: list) -> stdevEstimates:

    stdev_dict = dict(
        [(
            instrument_code,
            get_current_annualised_perc_stdev_for_instrument(data, instrument_code)
            )
            for instrument_code in instrument_list]
    )

    stdev = stdevEstimates(stdev_dict)
    return stdev


def get_current_annualised_perc_stdev_for_instrument(data, instrument_code):
    price = get_current_price_of_instrument(data, instrument_code)
    stdev_price = get_current_annualised_stdev_for_instrument(data, instrument_code)

    return stdev_price / price


def get_current_daily_stdev_for_instrument(data, instrument_code):
    rolling_daily_vol = get_daily_ts_stdev_of_adjusted_prices(data,
        instrument_code
    )
    if len(rolling_daily_vol) == 0:
        last_daily_vol = np.nan
    else:
        last_daily_vol = rolling_daily_vol.ffill().values[-1]

    return last_daily_vol


def get_current_annualised_stdev_for_instrument(data, instrument_code):
    last_daily_vol = get_current_daily_stdev_for_instrument(data, instrument_code)
    last_annual_vol = last_daily_vol * ROOT_BDAYS_INYEAR

    return last_annual_vol


def get_daily_ts_stdev_of_adjusted_prices(data, instrument_code):
    daily_returns = get_daily_returns(data, instrument_code)
    daily_std = daily_returns.rolling(30, min_periods=2).std()

    return daily_std


def get_list_of_positions_for_strategy_as_perc_of_capital(data, strategy_name):
    instrument_list = get_instruments_with_positions(data, strategy_name)
    positions_as_perc_of_capital = [
        get_perc_of_capital_position_size_for_instrument(data, strategy_name, instrument_code)
        for instrument_code in instrument_list]
    for instrument_code in instrument_list:
        get_perc_of_capital_position_size_for_instrument(data, strategy_name, instrument_code)

    return positions_as_perc_of_capital


def get_instruments_with_positions(data, strategy_name):
    diag_positions = diagPositions(data)
    instrument_list = diag_positions.get_list_of_instruments_for_strategy_with_position(strategy_name)

    return instrument_list


def get_instruments_with_positions_all_strategies(data):
    diag_positions = diagPositions(data)
    instrument_list = diag_positions.get_list_of_instruments_with_current_positions()
    return instrument_list


def get_perc_of_capital_position_size_for_instrument(
    data, strategy_name, instrument_code
):
    capital_base_fx = capital_for_strategy(data, strategy_name)
    exposure_base_fx = get_notional_exposure_in_base_currency_for_instrument(data, strategy_name, instrument_code)

    return exposure_base_fx / capital_base_fx


def get_perc_of_capital_position_size_for_instrument_across_strategies(
    data,  instrument_code
):
    capital_base_fx = total_capital(data)
    exposure_base_fx = get_notional_exposure_in_base_currency_for_instrument_across_strategies(data, instrument_code)

    return exposure_base_fx / capital_base_fx


def capital_for_strategy(data, strategy_name):
    data_capital = dataCapital(data)
    capital = data_capital.get_capital_for_strategy(
        strategy_name)
    if capital is missing_data:
        return 0.00001

    return capital


def total_capital(data):
    data_capital = dataCapital(data)
    total_capital = data_capital.get_current_total_capital()

    return total_capital


def get_perc_of_strategy_capital_for_instrument_per_contract(
    data, strategy_name, instrument_code
):
    capital_base_fx = capital_for_strategy(data, strategy_name)
    exposure_per_contract = get_exposure_per_contract_base_currency(
        data, instrument_code)

    return exposure_per_contract / capital_base_fx

def get_notional_exposure_in_base_currency_for_instrument(
    data, strategy_name, instrument_code
):

    exposure_per_contract = get_exposure_per_contract_base_currency(
        data, instrument_code)
    position = get_current_position_for_instrument_code(
        data, strategy_name, instrument_code
    )

    return exposure_per_contract * position


def get_notional_exposure_in_base_currency_for_instrument_across_strategies(
    data, instrument_code
):

    exposure_per_contract = get_exposure_per_contract_base_currency(
        data, instrument_code)
    position = get_current_position_for_instrument_code_across_strategies(
        data, instrument_code
    )

    return exposure_per_contract * position


def get_base_currency_risk_held_for_instrument_across_strategies(data, instrument_code):
    risk = get_base_currency_risk_per_lot_for_instrument(data, instrument_code)
    position = get_current_position_for_instrument_code_across_strategies(data, instrument_code)

    return risk*position


def get_base_currency_risk_per_lot_for_instrument(data, instrument_code):
    exposure_per_lot = get_exposure_per_contract_base_currency(data, instrument_code)
    annual_perc_stdev = get_current_annualised_perc_stdev_for_instrument(data, instrument_code)

    annual_base_currency_risk = exposure_per_lot * annual_perc_stdev

    return annual_base_currency_risk


def get_current_position_for_instrument_code(
        data, strategy_name, instrument_code):
    diag_positions = diagPositions(data)
    instrument_strategy = instrumentStrategy(strategy_name=strategy_name, instrument_code=instrument_code)

    current_position = diag_positions.get_current_position_for_instrument_strategy(instrument_strategy)

    return current_position


def get_current_position_for_instrument_code_across_strategies(data, instrument_code):
    diag_positions = diagPositions(data)
    position = diag_positions.get_current_instrument_position_across_strategies(instrument_code)

    return position


def get_exposure_per_contract_base_currency(data, instrument_code):
    point_size_base_currency = get_base_currency_point_size_per_contract(data, instrument_code)
    price = get_current_price_of_instrument(data, instrument_code)

    return point_size_base_currency * price


def get_base_currency_point_size_per_contract(data, instrument_code):
    diag_instruments = diagInstruments(data)
    point_size_base_currency = diag_instruments.get_point_size_base_currency(instrument_code)

    return point_size_base_currency


def get_current_price_of_instrument(data, instrument_code):
    price_series = get_price_series(data, instrument_code)
    if len(price_series)==0:
        return np.nan

    current_price = price_series.values[-1]

    return current_price


def get_daily_perc_returns(data, instrument_code):
    daily_returns = get_daily_returns(data, instrument_code)
    daily_prices = get_daily_price_series(data, instrument_code)

    return daily_returns / daily_prices


def get_daily_returns(data, instrument_code):
    daily_prices = get_daily_price_series(data, instrument_code)
    daily_returns = daily_prices.diff()

    return daily_returns


def get_daily_price_series(data, instrument_code):
    price_series = get_price_series(data, instrument_code)
    if len(price_series)==0:
        return price_series

    daily_prices = price_series.resample("1B").last()

    return daily_prices


def get_price_series(data, instrument_code):
    diag_prices = diagPrices(data)
    price_series = diag_prices.get_adjusted_prices(instrument_code)

    return price_series


def get_annual_perc_stdev_for_instrument(data, instrument_code):
    daily_price_stdev = get_current_daily_stdev_for_instrument(data, instrument_code)
    annual_price_stdev= daily_price_stdev * ROOT_BDAYS_INYEAR
    price = get_current_price_of_instrument(data, instrument_code)
    annual_perc_stdev = 100* annual_price_stdev / price

    return annual_perc_stdev


def get_risk_data_for_instrument(data, instrument_code):
    daily_price_stdev = get_current_daily_stdev_for_instrument(data, instrument_code)
    annual_price_stdev= daily_price_stdev * ROOT_BDAYS_INYEAR
    price = get_current_price_of_instrument(data, instrument_code)
    daily_perc_stdev = 100* daily_price_stdev / price
    annual_perc_stdev = 100* annual_price_stdev / price
    point_size_base = get_base_currency_point_size_per_contract(data, instrument_code)
    contract_exposure = point_size_base * price
    daily_risk_per_contract = daily_price_stdev * point_size_base
    annual_risk_per_contract = annual_price_stdev * point_size_base
    position = get_current_position_for_instrument_code_across_strategies(data, instrument_code)
    capital = total_capital(data)
    exposure_held_perc_capital = 100* position * contract_exposure / capital
    annual_risk_perc_capital = 100* annual_risk_per_contract * position / capital

    return dict(daily_price_stdev = daily_price_stdev,
                annual_price_stdev = annual_price_stdev,
                price = price,
                daily_perc_stdev = daily_perc_stdev,
                annual_perc_stdev = annual_perc_stdev,
                point_size_base = point_size_base,
                contract_exposure = contract_exposure,
                daily_risk_per_contract= daily_risk_per_contract,
                annual_risk_per_contract = annual_risk_per_contract,
                position = position,
                capital = capital,
                exposure_held_perc_capital = exposure_held_perc_capital,
                annual_risk_perc_capital = annual_risk_perc_capital)


def get_portfolio_risk_for_all_strategies(data):
    ## TOTAL PORTFOLIO RISK
    weights = get_perc_of_capital_position_size_all_strategies(data)
    instrument_list= list(weights.keys())
    cmatrix = get_correlation_matrix(data, instrument_list)
    std_dev = get_annualised_stdev_for_instruments(data, instrument_list)

    risk = get_annualised_risk_given_inputs(std_dev, cmatrix, weights)

    return risk

def get_perc_of_capital_position_size_all_strategies(
        data
        ) -> portfolioWeights:

    instrument_list = get_instruments_with_positions_all_strategies(data)
    weights = portfolioWeights([
        (instrument_code,
        get_perc_of_capital_position_size_for_instrument_across_strategies(data, instrument_code)
         )
        for instrument_code in instrument_list])

    return weights

def get_portfolio_risk_across_strategies(data):
    ## PORTFOLIO RISK PER STRATEGY
    diag_positions = diagPositions(data)
    strategy_list = diag_positions.get_list_of_strategies_with_positions()
    risk_across_strategies = dict([(strategy_name, get_portfolio_risk_for_strategy(data, strategy_name))
                  for strategy_name in strategy_list])

    df_of_capital_risk = pd.DataFrame(risk_across_strategies, index=['risk'])

    df_of_capital_risk = sorted_clean_df(df_of_capital_risk, sortby='risk')

    return df_of_capital_risk


def get_df_annualised_risk_as_perc_of_capital_per_instrument_across_strategies(data):
    ## RISK PER INSTRUMENT
    ## EQUAL TO ANNUALISED INSTRUMENT RISK PER CONTRACT IN BASE CCY MULTIPLIED BY POSITIONS HELD / CAPITAL
    instrument_list = get_instruments_with_positions_all_strategies(data)

    perc_of_capital_risk_of_positions_held = dict([(instrument_code,
                                                    get_annualised_perc_of_capital_risk_of_positions_held_for_instruments_across_strategies(data, instrument_code))
        for instrument_code in instrument_list
                ])

    df_of_capital_risk = pd.DataFrame(perc_of_capital_risk_of_positions_held, index=['risk'])
    df_of_capital_risk = sorted_clean_df(df_of_capital_risk, sortby='risk')

    return df_of_capital_risk


def sorted_clean_df(df_of_risk, sortby='risk'):
    df_of_risk = df_of_risk.transpose()
    df_of_risk = df_of_risk.dropna()
    df_of_risk = df_of_risk.sort_values(sortby)

    return df_of_risk