import datetime

import numpy as np
import pandas as pd

from syscore.dateutils import ROOT_BDAYS_INYEAR
from syscore.objects import header, table, body_text, missing_data
from syscore.optimisation_utils import sigma_from_corr_and_std

from sysproduction.data.positions import diagPositions
from sysproduction.data.capital import dataCapital
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.prices import diagPrices



# FIX ME A VERY INEFFICIENT REPORT THAT COULD REALLY DO WITH SOME CACHING...
# BUT THEN MAYBE CACHING SHOULD BE INTRODUCED MORE GENERALLY AT SYSPRODUCTION_DATA LEVEL?
# ALSO, WHY DO WE GET POSITIONS FOR WHICH THE CURRENT POSITION IS ZERO?

def risk_report(data):
    """
    Get risk report info
    """
    results_dict = calculate_risk_report_data(data)
    formatted_output = format_risk_report(results_dict)

    return formatted_output


def calculate_risk_report_data(data):
    ## Correlations, instrument risk calcs, risk per instrument, portfolio risk total, portfolio risk for strategies
    corr_data = get_correlation_matrix_all_instruments(data)
    instrument_risk_data = get_instrument_risk_table(data)
    strategy_risk = get_portfolio_risk_across_strategies(data)
    portfolio_risk_total = get_portfolio_risk_for_all_strategies(data)

    result_dict = dict(corr_data = corr_data, instrument_risk_data = instrument_risk_data,
                  portfolio_risk_total = portfolio_risk_total, strategy_risk = strategy_risk)

    return result_dict

def format_risk_report(results_dict):
    """
    Put the results into a printable format

    :param results_dict: dict of risk tables
    :return:
    """


    formatted_output = []

    formatted_output.append(
        header(
            "Risk report produced on %s" % str(
                datetime.datetime.now())))

    result1 = results_dict['portfolio_risk_total']*100
    result1_text = body_text("Total risk across all strategies, annualised percentage %.1f" % result1)
    formatted_output.append(result1_text)

    table2_df = results_dict['strategy_risk']*100
    table2_df = table2_df.round(1)
    table2 = table("Risk per strategy, annualised percentage", table2_df)
    formatted_output.append(table2)

    table3_df = results_dict['instrument_risk_data']
    table3_df = table3_df.round(1)
    table3 = table("Instrument risk", table3_df)
    formatted_output.append(table3)

    table4_df = results_dict['corr_data']
    table4_df = table4_df.round(2)
    table4 = table("Correlations", table4_df)
    formatted_output.append(table4)

    formatted_output.append(header("END OF RISK REPORT"))

    return formatted_output


def get_instrument_risk_table(data):
    ## INSTRUMENT RISK (daily %, annual %, return space daily and annual, base currency per contract daily and annual, positions)
    instrument_list = get_instruments_with_positions_all_strategies(data)
    risk_data_list = dict([(instrument_code, get_risk_data_for_instrument(data, instrument_code))
                           for instrument_code in instrument_list])
    risk_df = pd.DataFrame(risk_data_list)
    risk_df = sorted_clean_df(risk_df, 'annual_risk_perc_capital')

    return risk_df

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
    instrument_list = get_instruments_with_positions_all_strategies(data)
    weights = [
        get_perc_of_capital_position_size_for_instrument_across_strategies(data, instrument_code)
        for instrument_code in instrument_list]

    cmatrix = get_correlation_matrix(data, instrument_list)
    std_dev = get_list_of_annualised_stdev_of_instruments(data, instrument_list)

    risk = get_annualised_risk_given_inputs(std_dev, cmatrix, weights)

    return risk

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

def get_annualised_perc_of_capital_risk_of_positions_held_for_instruments_across_strategies(data, instrument_code):
    capital_base_fx = total_capital(data)
    base_currency_risk = get_base_currency_risk_held_for_instrument_across_strategies(data, instrument_code)

    perc_of_capital_risk = base_currency_risk / capital_base_fx

    return perc_of_capital_risk


def get_portfolio_risk_for_strategy(data, strategy_name):
    instrument_list = get_instruments_with_positions(data, strategy_name)
    weights = [
        get_perc_of_capital_position_size_for_instrument(data, strategy_name, instrument_code)
        for instrument_code in instrument_list]

    cmatrix = get_correlation_matrix(data, instrument_list)
    std_dev = get_list_of_annualised_stdev_of_instruments(data, instrument_list)

    risk = get_annualised_risk_given_inputs(std_dev, cmatrix, weights)

    return risk

def get_annualised_risk_given_inputs(std_dev, cmatrix, weights):
    weights = np.array(weights)
    std_dev = np.array(std_dev)
    std_dev, cmatrix, weights = clean_values(std_dev, cmatrix, weights)
    sigma = sigma_from_corr_and_std(std_dev, cmatrix)

    portfolio_variance = weights.dot(sigma).dot(weights.transpose())
    portfolio_std = portfolio_variance**.5

    return portfolio_std

def clean_values(std_dev, cmatrix, weights):
    cmatrix[np.isnan(cmatrix)] = 1.0
    weights[np.isnan(weights)] = 0.0
    std_dev[np.isnan(std_dev)] = 100.0

    return std_dev, cmatrix, weights

def get_correlation_matrix_all_instruments(data):
    instrument_list = get_instruments_with_positions_all_strategies(data)
    cmatrix = get_correlation_matrix(data, instrument_list)

    return cmatrix

def get_correlation_matrix(data, instrument_list):
    perc_returns = dict([(instrument_code, get_daily_perc_returns(data, instrument_code))
                for instrument_code in instrument_list])
    price_df = pd.DataFrame(perc_returns)

    # daily use last 6 months
    price_df = price_df[-128:]
    price_corr = price_df.corr()

    return price_corr


def get_list_of_annualised_stdev_of_instruments(data, instrument_list):
    stdev_list = [get_current_annualised_perc_stdev_for_instrument(data, instrument_code)
                  for instrument_code in instrument_list]
    return stdev_list

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
    current_position = diag_positions.get_position_for_strategy_and_instrument(
        strategy_name, instrument_code
    )

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