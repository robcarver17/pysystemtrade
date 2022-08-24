import numpy as np
import pandas as pd

from syscore.dateutils import ROOT_BDAYS_INYEAR, BUSINESS_DAYS_IN_YEAR
from syscore.genutils import progressBar

from sysobjects.production.tradeable_object import instrumentStrategy
from sysproduction.data.risk import get_correlation_matrix_for_instrument_returns, \
    get_annualised_stdev_perc_of_instruments, get_current_annualised_perc_stdev_for_instrument, \
    get_current_daily_perc_stdev_for_instrument, get_daily_ts_stdev_of_prices, get_exposure_per_contract_base_currency, \
    get_base_currency_point_size_per_contract
from sysproduction.reporting.data.constants import RISK_TARGET_ASSUMED, INSTRUMENT_WEIGHT_ASSUMED, IDM_ASSUMED, \
    MIN_CONTRACTS_HELD

from sysquant.estimators.covariance import (
    get_annualised_risk,
)
from sysquant.estimators.correlations import correlationEstimate
from sysquant.estimators.clustering_correlations import assets_in_cluster_order
from sysquant.optimisation.weights import portfolioWeights

from sysproduction.data.capital import dataCapital, dataMargin, capital_for_strategy
from sysproduction.data.positions import diagPositions
from sysproduction.data.prices import get_list_of_instruments, get_current_price_of_instrument

DAILY_RISK_CALC_LOOKBACK = int(BUSINESS_DAYS_IN_YEAR * 2)

## only used for reporting purposes

def get_margin_usage(data) -> float:
    capital = get_current_capital(data)
    margin = get_current_margin(data)
    margin_usage = margin / capital

    return margin_usage

def get_current_capital(data) -> float:
    data_capital = dataCapital(data)
    capital = data_capital.get_current_total_capital()
    return capital

def get_current_margin(data) -> float:
    data_margin = dataMargin(data)
    margin = data_margin.get_current_total_margin()

    return margin

def minimum_capital_table(data,
                          only_held_instruments=False,
                          risk_target =RISK_TARGET_ASSUMED,
                          min_contracts_held =MIN_CONTRACTS_HELD,
                          idm =IDM_ASSUMED,
                          instrument_weight =INSTRUMENT_WEIGHT_ASSUMED
                          ) -> pd.DataFrame:

    instrument_risk_table = get_instrument_risk_table(data,
                                                      only_held_instruments=only_held_instruments)

    min_capital_pd = from_risk_table_to_min_capital(instrument_risk_table,
                                                 risk_target=risk_target,
                                                    min_contracts_held=min_contracts_held,
                                                    idm=idm,
                                                    instrument_weight=instrument_weight)

    return min_capital_pd

def from_risk_table_to_min_capital(instrument_risk_table: pd.DataFrame,
                                   risk_target =RISK_TARGET_ASSUMED,
                                   min_contracts_held=MIN_CONTRACTS_HELD,
                                   idm=IDM_ASSUMED,
                                   instrument_weight=INSTRUMENT_WEIGHT_ASSUMED
                                   ) -> pd.DataFrame:

    base_multiplier = instrument_risk_table.point_size_base
    price = instrument_risk_table.price
    ann_perc_stdev = instrument_risk_table.annual_perc_stdev

    ## perc stdev is 100% = 100, so divide by 100
    ## risk target is 20 = 20, so divide by 100
    ## These two effects cancel

    single_contract_min_capital = base_multiplier * price * ann_perc_stdev / \
                         (risk_target)

    min_capital_series = min_contracts_held * single_contract_min_capital / \
                         (idm * instrument_weight )

    instrument_list = instrument_risk_table.index
    instrument_count = len(instrument_list)

    min_capital_pd = pd.concat([base_multiplier,
                                price,
                                ann_perc_stdev,
                                pd.Series([risk_target]*instrument_count, index = instrument_list),
                                single_contract_min_capital,
                                pd.Series([min_contracts_held] * instrument_count, index=instrument_list),
                                pd.Series([instrument_weight] * instrument_count, index=instrument_list),
                                pd.Series([idm] * instrument_count, index=instrument_list),
                                min_capital_series], axis=1)
    min_capital_pd.columns = ['point_size_base',
                              'price',
                              'annual_perc_stdev',
                              'risk_target',
                              'minimum_capital_one_contract',
                              'minimum_position_contracts',
                              'instrument_weight',
                              'IDM',
                              'minimum_capital'
                              ]

    return min_capital_pd

def get_instrument_risk_table(data, only_held_instruments=True):
    ## INSTRUMENT RISK (daily %, annual %, return space daily and annual, base currency per contract daily and annual, positions)
    if only_held_instruments:
        instrument_list = get_instruments_with_positions_all_strategies(data)
    else:
        instrument_list = get_list_of_instruments()

    p = progressBar(len(instrument_list))
    risk_data_list = []
    for instrument_code in instrument_list:
        risk_this_instrument = get_risk_data_for_instrument(data, instrument_code)
        risk_data_list.append(risk_this_instrument)
        p.iterate()

    p.finished()

    risk_df = pd.DataFrame(risk_data_list, index=instrument_list).transpose()
    risk_df = sorted_clean_df(risk_df, "annual_risk_perc_capital")

    return risk_df


def get_risk_data_for_instrument(data, instrument_code):
    daily_price_stdev = get_current_daily_stdev_for_instrument(data, instrument_code)
    annual_price_stdev = daily_price_stdev * ROOT_BDAYS_INYEAR
    price = get_current_price_of_instrument(data, instrument_code)
    daily_perc_stdev100 = (
            get_current_daily_perc_stdev_for_instrument(data, instrument_code) * 100
    )
    annual_perc_stdev100 = daily_perc_stdev100 * ROOT_BDAYS_INYEAR
    point_size_base = get_base_currency_point_size_per_contract(data, instrument_code)
    contract_exposure = point_size_base * price
    daily_risk_per_contract = daily_price_stdev * point_size_base
    annual_risk_per_contract = annual_price_stdev * point_size_base
    position = get_current_position_for_instrument_code_across_strategies(
        data, instrument_code
    )
    capital = total_capital(data)
    exposure_held_perc_capital = 100 * position * contract_exposure / capital
    annual_risk_perc_capital = 100 * annual_risk_per_contract * position / capital

    return dict(
        daily_price_stdev=daily_price_stdev,
        annual_price_stdev=annual_price_stdev,
        price=price,
        daily_perc_stdev=daily_perc_stdev100,
        annual_perc_stdev=annual_perc_stdev100,
        point_size_base=point_size_base,
        contract_exposure=contract_exposure,
        daily_risk_per_contract=daily_risk_per_contract,
        annual_risk_per_contract=annual_risk_per_contract,
        position=position,
        capital=capital,
        exposure_held_perc_capital=exposure_held_perc_capital,
        annual_risk_perc_capital=annual_risk_perc_capital,
    )


def get_portfolio_risk_for_all_strategies(data):
    ## TOTAL PORTFOLIO RISK
    weights = get_perc_of_capital_position_size_all_strategies(data)
    instrument_list = list(weights.keys())
    cmatrix = get_correlation_matrix_for_instrument_returns(data, instrument_list)
    std_dev = get_annualised_stdev_perc_of_instruments(data, instrument_list)

    risk = get_annualised_risk(std_dev, cmatrix, weights)

    return risk


def get_perc_of_capital_position_size_all_strategies(data) -> portfolioWeights:

    instrument_list = get_instruments_with_positions_all_strategies(data)
    weights = portfolioWeights(
        [
            (
                instrument_code,
                get_perc_of_capital_position_size_for_instrument_across_strategies(
                    data, instrument_code
                ),
            )
            for instrument_code in instrument_list
        ]
    )

    return weights


def get_portfolio_risk_across_strategies(data):
    ## PORTFOLIO RISK PER STRATEGY
    diag_positions = diagPositions(data)
    strategy_list = diag_positions.get_list_of_strategies_with_positions()
    risk_across_strategies = dict(
        [
            (strategy_name, get_portfolio_risk_for_strategy(data, strategy_name))
            for strategy_name in strategy_list
        ]
    )

    df_of_capital_risk = pd.DataFrame(risk_across_strategies, index=["risk"])

    df_of_capital_risk = sorted_clean_df(df_of_capital_risk, sortby="risk")

    return df_of_capital_risk


def get_df_annualised_risk_as_perc_of_capital_per_instrument_across_strategies(data):
    ## RISK PER INSTRUMENT
    ## EQUAL TO ANNUALISED INSTRUMENT RISK PER CONTRACT IN BASE CCY MULTIPLIED BY POSITIONS HELD / CAPITAL
    instrument_list = get_instruments_with_positions_all_strategies(data)

    perc_of_capital_risk_of_positions_held = dict(
        [
            (
                instrument_code,
                get_annualised_perc_of_capital_risk_of_positions_held_for_instruments_across_strategies(
                    data, instrument_code
                ),
            )
            for instrument_code in instrument_list
        ]
    )

    df_of_capital_risk = pd.DataFrame(
        perc_of_capital_risk_of_positions_held, index=["risk"]
    )
    df_of_capital_risk = sorted_clean_df(df_of_capital_risk, sortby="risk")

    return df_of_capital_risk


def get_annualised_perc_of_capital_risk_of_positions_held_for_instruments_across_strategies(
    data, instrument_code
):
    capital_base_fx = total_capital(data)
    base_currency_risk = get_base_currency_risk_held_for_instrument_across_strategies(
        data, instrument_code
    )

    perc_of_capital_risk = base_currency_risk / capital_base_fx

    return perc_of_capital_risk


def get_portfolio_risk_for_strategy(data, strategy_name):

    weights = get_perc_of_capital_position_size_across_instruments_for_strategy(
        data, strategy_name
    )
    instrument_list = list(weights.keys())
    cmatrix = get_correlation_matrix_for_instrument_returns(data, instrument_list)
    std_dev = get_annualised_stdev_perc_of_instruments(data, instrument_list)

    risk = get_annualised_risk(std_dev, cmatrix, weights)

    return risk


def get_perc_of_capital_position_size_across_instruments_for_strategy(
    data, strategy_name: str
) -> portfolioWeights:

    instrument_list = get_instruments_with_positions(data, strategy_name)
    weights = portfolioWeights(
        [
            (
                instrument_code,
                get_perc_of_capital_position_size_for_instrument(
                    data, strategy_name, instrument_code
                ),
            )
            for instrument_code in instrument_list
        ]
    )

    return weights


def get_correlation_matrix_all_instruments(data) -> correlationEstimate:
    instrument_list = get_instruments_with_positions_all_strategies(data)
    cmatrix = get_correlation_matrix_for_instrument_returns(data, instrument_list)

    cmatrix = cmatrix.ordered_correlation_matrix()

    return cmatrix

def cluster_correlation_matrix(cmatrix: correlationEstimate) -> correlationEstimate:
    cluster_size = min(5, int(cmatrix.size/3))
    new_order = assets_in_cluster_order(cmatrix, cluster_size=cluster_size)
    cmatrix = cmatrix.list_in_key_order(new_order)

    return cmatrix


def get_current_annualised_stdev_for_instrument(data, instrument_code):
    last_daily_vol = get_current_daily_stdev_for_instrument(data, instrument_code)
    last_annual_vol = last_daily_vol * ROOT_BDAYS_INYEAR

    return last_annual_vol


def get_current_daily_stdev_for_instrument(data, instrument_code):
    rolling_daily_vol = get_daily_ts_stdev_of_prices(data, instrument_code)
    if len(rolling_daily_vol) == 0:
        last_daily_vol = np.nan
    else:
        last_daily_vol = rolling_daily_vol.ffill().values[-1]

    return last_daily_vol


def get_list_of_positions_for_strategy_as_perc_of_capital(data, strategy_name):
    instrument_list = get_instruments_with_positions(data, strategy_name)
    positions_as_perc_of_capital = [
        get_perc_of_capital_position_size_for_instrument(
            data, strategy_name, instrument_code
        )
        for instrument_code in instrument_list
    ]
    for instrument_code in instrument_list:
        get_perc_of_capital_position_size_for_instrument(
            data, strategy_name, instrument_code
        )

    return positions_as_perc_of_capital


def get_instruments_with_positions(data, strategy_name):
    diag_positions = diagPositions(data)
    instrument_list = diag_positions.get_list_of_instruments_for_strategy_with_position(
        strategy_name
    )

    return instrument_list


def get_instruments_with_positions_all_strategies(data):
    diag_positions = diagPositions(data)
    instrument_list = diag_positions.get_list_of_instruments_with_current_positions()
    return instrument_list


def get_perc_of_capital_position_size_for_instrument(
    data, strategy_name, instrument_code
):
    capital_base_fx = capital_for_strategy(data, strategy_name)
    exposure_base_fx = get_notional_exposure_in_base_currency_for_instrument(
        data, strategy_name, instrument_code
    )

    return exposure_base_fx / capital_base_fx


def get_perc_of_capital_position_size_for_instrument_across_strategies(
    data, instrument_code
):
    capital_base_fx = total_capital(data)
    exposure_base_fx = (
        get_notional_exposure_in_base_currency_for_instrument_across_strategies(
            data, instrument_code
        )
    )

    return exposure_base_fx / capital_base_fx


def total_capital(data):
    data_capital = dataCapital(data)
    total_capital = data_capital.get_current_total_capital()

    return total_capital


def get_notional_exposure_in_base_currency_for_instrument(
    data, strategy_name, instrument_code
):

    exposure_per_contract = get_exposure_per_contract_base_currency(
        data, instrument_code
    )
    position = get_current_position_for_instrument_code(
        data, strategy_name, instrument_code
    )

    return exposure_per_contract * position


def get_notional_exposure_in_base_currency_for_instrument_across_strategies(
    data, instrument_code
):

    exposure_per_contract = get_exposure_per_contract_base_currency(
        data, instrument_code
    )
    position = get_current_position_for_instrument_code_across_strategies(
        data, instrument_code
    )

    return exposure_per_contract * position


def get_base_currency_risk_held_for_instrument_across_strategies(data, instrument_code):
    risk = get_base_currency_risk_per_lot_for_instrument(data, instrument_code)
    position = get_current_position_for_instrument_code_across_strategies(
        data, instrument_code
    )

    return risk * position


def get_base_currency_risk_per_lot_for_instrument(data, instrument_code):
    exposure_per_lot = get_exposure_per_contract_base_currency(data, instrument_code)
    annual_perc_stdev = get_current_annualised_perc_stdev_for_instrument(
        data, instrument_code
    )

    annual_base_currency_risk = exposure_per_lot * annual_perc_stdev

    return annual_base_currency_risk


def get_current_position_for_instrument_code(data, strategy_name, instrument_code):
    diag_positions = diagPositions(data)
    instrument_strategy = instrumentStrategy(
        strategy_name=strategy_name, instrument_code=instrument_code
    )

    current_position = diag_positions.get_current_position_for_instrument_strategy(
        instrument_strategy
    )

    return current_position


def get_current_position_for_instrument_code_across_strategies(data, instrument_code):
    diag_positions = diagPositions(data)
    position = diag_positions.get_current_instrument_position_across_strategies(
        instrument_code
    )

    return position


def sorted_clean_df(df_of_risk, sortby="risk"):
    df_of_risk = df_of_risk.transpose()
    df_of_risk = df_of_risk.dropna()
    df_of_risk = df_of_risk.sort_values(sortby)

    return df_of_risk
