from typing import Union, Dict
import numpy as np
import pandas as pd
from statsmodels.formula import api as sm

from syscore.dateutils import ROOT_BDAYS_INYEAR, n_days_ago, CALENDAR_DAYS_IN_YEAR
from syscore.interactive.progress_bar import progressBar
from syscore.constants import arg_not_supplied
from syscore.pandas.frequency import resample_prices_to_business_day_index
from sysdata.data_blob import dataBlob


from sysobjects.production.tradeable_object import instrumentStrategy
from sysproduction.data.risk import (
    get_correlation_matrix_for_instrument_returns,
    get_annualised_stdev_perc_of_instruments,
    get_current_annualised_perc_stdev_for_instrument,
    get_current_daily_perc_stdev_for_instrument,
    get_daily_ts_stdev_of_prices,
    get_exposure_per_contract_base_currency,
    get_base_currency_point_size_per_contract,
)
from sysproduction.data.instruments import diagInstruments
from sysproduction.reporting.data.constants import (
    RISK_TARGET_ASSUMED,
    INSTRUMENT_WEIGHT_ASSUMED,
    IDM_ASSUMED,
    MIN_CONTRACTS_HELD,
)

from sysquant.estimators.covariance import (
    get_annualised_risk,
)
from sysquant.estimators.correlations import correlationEstimate
from sysquant.estimators.clustering_correlations import assets_in_cluster_order
from sysquant.estimators.stdev_estimator import stdevEstimates
from sysquant.optimisation.weights import portfolioWeights

from sysproduction.data.capital import dataCapital, dataMargin, capital_for_strategy
from sysproduction.data.positions import diagPositions
from sysproduction.data.prices import (
    get_list_of_instruments,
    get_current_price_of_instrument,
    diagPrices,
)


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


def minimum_capital_table(
    data,
    only_held_instruments=False,
    risk_target=RISK_TARGET_ASSUMED,
    min_contracts_held=MIN_CONTRACTS_HELD,
    idm=IDM_ASSUMED,
    instrument_weight=INSTRUMENT_WEIGHT_ASSUMED,
) -> pd.DataFrame:

    instrument_risk_table = get_instrument_risk_table(
        data, only_held_instruments=only_held_instruments
    )

    min_capital_pd = from_risk_table_to_min_capital(
        instrument_risk_table,
        risk_target=risk_target,
        min_contracts_held=min_contracts_held,
        idm=idm,
        instrument_weight=instrument_weight,
    )

    return min_capital_pd


def from_risk_table_to_min_capital(
    instrument_risk_table: pd.DataFrame,
    risk_target=RISK_TARGET_ASSUMED,
    min_contracts_held=MIN_CONTRACTS_HELD,
    idm=IDM_ASSUMED,
    instrument_weight=INSTRUMENT_WEIGHT_ASSUMED,
) -> pd.DataFrame:

    base_multiplier = instrument_risk_table.point_size_base
    price = instrument_risk_table.price
    ann_perc_stdev = instrument_risk_table.annual_perc_stdev

    ## perc stdev is 100% = 100, so divide by 100
    ## risk target is 20 = 20, so divide by 100
    ## These two effects cancel

    single_contract_min_capital = (
        base_multiplier * price * ann_perc_stdev / (risk_target)
    )

    min_capital_series = (
        min_contracts_held * single_contract_min_capital / (idm * instrument_weight)
    )

    instrument_list = instrument_risk_table.index
    instrument_count = len(instrument_list)

    min_capital_pd = pd.concat(
        [
            base_multiplier,
            price,
            ann_perc_stdev,
            pd.Series([risk_target] * instrument_count, index=instrument_list),
            single_contract_min_capital,
            pd.Series([min_contracts_held] * instrument_count, index=instrument_list),
            pd.Series([instrument_weight] * instrument_count, index=instrument_list),
            pd.Series([idm] * instrument_count, index=instrument_list),
            min_capital_series,
        ],
        axis=1,
    )
    min_capital_pd.columns = [
        "point_size_base",
        "price",
        "annual_perc_stdev",
        "risk_target",
        "minimum_capital_one_contract",
        "minimum_position_contracts",
        "instrument_weight",
        "IDM",
        "minimum_capital",
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

    p.close()

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


class portfolioRisks(object):
    def __init__(self, data):
        self._data = data

    def get_beta_loadings_by_asset_class(self) -> pd.Series:
        loadings_as_dict = calculate_dict_of_beta_loadings_by_asset_class_given_weights(
            weights=self.weights,
            dict_of_betas=self.dict_of_betas,
            dict_of_asset_classes=self.dict_of_asset_classes_for_instruments,
        )

        return pd.Series(loadings_as_dict)

    def get_portfolio_risk_for_all_strategies(self) -> float:
        ## TOTAL PORTFOLIO RISK
        weights = self.weights
        cmatrix = self.correlation_matrix
        std_dev = self.stdev

        risk = get_annualised_risk(std_dev, cmatrix, weights)

        return risk

    def get_pd_series_of_risk_by_asset_class(self) -> pd.Series:
        asset_classes = self.dict_of_asset_classes_for_instruments
        weights = self.weights
        cmatrix = self.correlation_matrix
        std_dev = self.stdev

        risk_pd_series = get_pd_series_of_risk_by_asset_class(
            asset_classes=asset_classes, weights=weights, cmatrix=cmatrix, stdev=std_dev
        )

        return risk_pd_series

    @property
    def dict_of_asset_classes_for_instruments(self) -> dict:
        asset_classes = get_dict_of_asset_classes_for_instrument_list(
            self.data, self.instrument_list
        )
        return asset_classes

    @property
    def correlation_matrix(self) -> correlationEstimate:
        instrument_list = self.instrument_list
        cmatrix = get_correlation_matrix_for_instrument_returns(
            self.data, instrument_list
        )

        return cmatrix

    @property
    def stdev(self) -> stdevEstimates:
        stdev = get_annualised_stdev_perc_of_instruments(
            self.data, self.instrument_list
        )
        return stdev

    @property
    def instrument_list(self):
        instrument_list = list(self.weights.keys())
        return instrument_list

    @property
    def weights(self) -> portfolioWeights:
        weights = get_perc_of_capital_position_size_all_strategies(self.data)
        return weights

    @property
    def dict_of_betas(self) -> dict:
        return dict_of_beta_by_instrument(
            perc_returns=self.recent_perc_returns,
            dict_of_asset_classes=self.dict_of_asset_classes_for_instruments,
            equally_weighted_returns_across_asset_classes=self.equally_weighted_returns_across_asset_classes,
        )

    @property
    def recent_perc_returns(self) -> pd.DataFrame:
        perc_returns = last_years_perc_returns_for_list_of_instruments(
            data=self.data, list_of_instruments=self.instrument_list
        )
        return perc_returns

    @property
    def equally_weighted_returns_across_asset_classes(self):
        return get_equally_weighted_returns_across_asset_classes(
            dict_of_asset_classes=self.dict_of_asset_classes_for_instruments,
            perc_returns=self.recent_perc_returns,
        )

    @property
    def data(self):
        return self._data


def get_pd_series_of_risk_by_asset_class(
    asset_classes: dict,
    weights: portfolioWeights,
    cmatrix: correlationEstimate,
    stdev: stdevEstimates,
) -> pd.Series:

    unique_asset_classes = list(set(list(asset_classes.values())))
    unique_asset_classes.sort()

    list_of_risks = [
        get_risk_for_asset_class(
            asset_class,
            asset_classes=asset_classes,
            weights=weights,
            cmatrix=cmatrix,
            stdev=stdev,
        )
        for asset_class in unique_asset_classes
    ]

    risk_as_series = pd.Series(list_of_risks, index=unique_asset_classes)

    return risk_as_series


def get_risk_for_asset_class(
    asset_class: str,
    asset_classes: dict,
    weights: portfolioWeights,
    cmatrix: correlationEstimate,
    stdev: stdevEstimates,
) -> float:

    instruments_in_asset_class = [
        instrument_code
        for instrument_code, instrument_asset_class in asset_classes.items()
        if instrument_asset_class == asset_class
    ]
    asset_class_weights = weights.subset(instruments_in_asset_class)
    asset_class_cmatrix = cmatrix.subset(instruments_in_asset_class)
    asset_class_stdev = stdev.subset(instruments_in_asset_class)

    risk = get_annualised_risk(
        std_dev=asset_class_stdev,
        cmatrix=asset_class_cmatrix,
        weights=asset_class_weights,
    )

    return risk


def get_dict_of_asset_classes_for_instrument_list(data, instrument_list: list) -> dict:

    diag_instruments = diagInstruments(data)
    asset_classes = dict(
        [
            (instrument_code, diag_instruments.get_asset_class(instrument_code))
            for instrument_code in instrument_list
        ]
    )

    return asset_classes


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
    cluster_size = min(5, int(cmatrix.size / 3))
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


def get_asset_classes_for_instrument_list(data, instrument_codes: list) -> dict:
    diag_instruments = diagInstruments(data)

    dict_of_asset_classes = dict(
        [
            (instrument_code, diag_instruments.get_asset_class(instrument_code))
            for instrument_code in instrument_codes
        ]
    )

    return dict_of_asset_classes


def calculate_dict_of_beta_loadings_by_asset_class_given_weights(
    weights: portfolioWeights, dict_of_betas: dict, dict_of_asset_classes: dict
) -> dict:

    dict_of_beta_loadings_per_instrument = (
        calculate_dict_of_beta_loadings_per_instrument(
            dict_of_betas=dict_of_betas, weights=weights
        )
    )

    beta_loadings_across_asset_classes = calculate_beta_loadings_across_asset_classes(
        dict_of_asset_classes=dict_of_asset_classes,
        dict_of_beta_loadings_per_instrument=dict_of_beta_loadings_per_instrument,
    )

    return beta_loadings_across_asset_classes


def calculate_dict_of_beta_loadings_per_instrument(
    dict_of_betas: dict, weights: portfolioWeights
) -> dict:

    list_of_instruments = dict_of_betas.keys()

    dict_of_beta_loadings_per_instrument = dict(
        [
            (instrument_code, dict_of_betas[instrument_code] * weights[instrument_code])
            for instrument_code in list_of_instruments
        ]
    )

    return dict_of_beta_loadings_per_instrument


def calculate_beta_loadings_across_asset_classes(
    dict_of_asset_classes: dict, dict_of_beta_loadings_per_instrument: dict
) -> dict:

    list_of_asset_classes = list(set(list(dict_of_asset_classes.values())))
    beta_loadings_across_asset_classes = dict(
        [
            (
                asset_class,
                calculate_beta_loading_for_asset_class(
                    asset_class=asset_class,
                    dict_of_asset_classes=dict_of_asset_classes,
                    dict_of_beta_loadings_per_instrument=dict_of_beta_loadings_per_instrument,
                ),
            )
            for asset_class in list_of_asset_classes
        ]
    )

    return beta_loadings_across_asset_classes


def calculate_beta_loading_for_asset_class(
    asset_class: str,
    dict_of_asset_classes: dict,
    dict_of_beta_loadings_per_instrument: dict,
) -> dict:

    relevant_instruments = [
        instrument_code
        for instrument_code, asset_class_for_instrument in dict_of_asset_classes.items()
        if asset_class == asset_class_for_instrument
        and instrument_code in dict_of_beta_loadings_per_instrument
    ]

    relevant_beta_loads = np.array(
        [
            dict_of_beta_loadings_per_instrument[instrument_code]
            for instrument_code in relevant_instruments
        ]
    )

    return np.nansum(relevant_beta_loads)


def get_beta_for_instrument_list(
    data: dataBlob, dict_of_asset_classes: dict, index_risk: float = arg_not_supplied
):

    list_of_instruments = list(dict_of_asset_classes.keys())
    perc_returns = last_years_perc_returns_for_list_of_instruments(
        data=data, list_of_instruments=list_of_instruments
    )
    equally_weighted_returns_across_asset_classes = (
        get_equally_weighted_returns_across_asset_classes(
            dict_of_asset_classes=dict_of_asset_classes,
            perc_returns=perc_returns,
            index_risk=index_risk,
        )
    )
    dict_of_betas = dict_of_beta_by_instrument(
        dict_of_asset_classes=dict_of_asset_classes,
        perc_returns=perc_returns,
        equally_weighted_returns_across_asset_classes=equally_weighted_returns_across_asset_classes,
    )

    return dict_of_betas


def last_years_perc_returns_for_list_of_instruments(
    data: dataBlob, list_of_instruments: list
) -> pd.DataFrame:
    diag_prices = diagPrices(data)
    adj_prices_as_dict = dict(
        (instrument_code, diag_prices.get_adjusted_prices(instrument_code))
        for instrument_code in list_of_instruments
    )

    adj_prices_as_df = pd.concat(adj_prices_as_dict, axis=1)
    adj_prices_as_df.columns = list_of_instruments
    daily_adj_prices_as_df = resample_prices_to_business_day_index(adj_prices_as_df)
    last_year_daily_adj_prices_as_df = daily_adj_prices_as_df[
        n_days_ago(CALENDAR_DAYS_IN_YEAR) :
    ]
    perc_returns = (
        last_year_daily_adj_prices_as_df - last_year_daily_adj_prices_as_df.shift(1)
    ) / last_year_daily_adj_prices_as_df.shift(1)

    return perc_returns


def get_equally_weighted_returns_across_asset_classes(
    dict_of_asset_classes: dict,
    perc_returns: pd.DataFrame,
    index_risk: float = arg_not_supplied,
) -> pd.DataFrame:

    list_of_asset_classes = list(set(list(dict_of_asset_classes.values())))

    results_as_list = [
        get_equally_weighted_returns_for_asset_class(
            asset_class=asset_class,
            dict_of_asset_classes=dict_of_asset_classes,
            perc_returns=perc_returns,
            index_risk=index_risk,
        )
        for asset_class in list_of_asset_classes
    ]

    results_as_pd = pd.concat(results_as_list, axis=1)
    results_as_pd.columns = list_of_asset_classes

    return results_as_pd


def get_equally_weighted_returns_for_asset_class(
    asset_class: str,
    dict_of_asset_classes: dict,
    perc_returns: pd.DataFrame,
    index_risk: float = arg_not_supplied,
) -> pd.Series:

    instruments_in_asset_class = [
        instrument
        for instrument, asset_class_for_instrument in dict_of_asset_classes.items()
        if asset_class == asset_class_for_instrument
    ]
    perc_returns_for_asset_class = perc_returns[instruments_in_asset_class]
    ew_index_returns = calculate_equal_returns_to_avg_vol(
        perc_returns_for_asset_class, index_risk=index_risk
    )

    return ew_index_returns


def calculate_equal_returns_to_avg_vol(
    perc_returns_for_asset_class: pd.DataFrame, index_risk: float = arg_not_supplied
) -> pd.Series:

    std_by_instrument = perc_returns_for_asset_class.std(axis=0)
    perc_returns_for_asset_class_vol_norm = (
        perc_returns_for_asset_class / std_by_instrument
    )
    avg_vol_norm_perc_returns = perc_returns_for_asset_class_vol_norm.mean(axis=1)

    if index_risk is arg_not_supplied:
        ## normalise to average risk of instruments in asset class
        avg_std = std_by_instrument.mean()
        asset_class_return_index = avg_vol_norm_perc_returns * avg_std
    else:
        ## normalise to provided index_risk; 20 = 20% per year
        index_risk_as_daily = index_risk / (ROOT_BDAYS_INYEAR * 100)
        asset_class_return_index = avg_vol_norm_perc_returns * index_risk_as_daily

    return asset_class_return_index


def dict_of_beta_by_instrument(
    dict_of_asset_classes: dict,
    perc_returns: pd.DataFrame,
    equally_weighted_returns_across_asset_classes: pd.DataFrame,
) -> dict:

    list_of_instruments = list(set(list(dict_of_asset_classes.keys())))
    dict_of_betas: Dict[str, float] = {}
    for instrument_code in list_of_instruments:
        beta = beta_for_instrument(
            instrument_code=instrument_code,
            perc_returns=perc_returns,
            dict_of_asset_classes=dict_of_asset_classes,
            equally_weighted_returns_across_asset_classes=equally_weighted_returns_across_asset_classes,
        )
        if beta is not None:
            dict_of_betas[instrument_code] = beta
    return dict_of_betas


def beta_for_instrument(
    instrument_code: str,
    dict_of_asset_classes: dict,
    perc_returns: pd.DataFrame,
    equally_weighted_returns_across_asset_classes: pd.DataFrame,
) -> Union[None, float]:

    asset_class = dict_of_asset_classes[instrument_code]
    perc_returns_for_instrument = perc_returns[instrument_code]
    perc_returns_for_asset_class = equally_weighted_returns_across_asset_classes[
        asset_class
    ]

    both_returns = pd.concat(
        [perc_returns_for_instrument, perc_returns_for_asset_class], axis=1
    )
    both_returns.columns = ["y", "x"]
    both_returns = both_returns.dropna()
    if not both_returns.empty:

        reg_result = sm.ols(formula="y ~ x", data=both_returns).fit()
        beta = reg_result.params.x

        return beta
