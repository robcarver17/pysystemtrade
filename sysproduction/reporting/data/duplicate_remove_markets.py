import numpy as np
import pandas as pd
from dataclasses import dataclass

from syscore.objects import missing_data, named_object
from sysdata.config.instruments import generate_matching_duplicate_dict
from sysdata.config.production_config import get_production_config
from sysproduction.reporting.data.constants import MAX_SR_COST, MIN_VOLUME_CONTRACTS_DAILY, MIN_VOLUME_RISK_DAILY

from sysproduction.reporting.reporting_functions import table

from sysproduction.reporting.data.costs import (
    get_table_of_SR_costs,
)
from sysproduction.reporting.data.volume import get_liquidity_data_df
from sysproduction.reporting.data.risk import (
    get_instrument_risk_table)

CHANGE_FLAG = "** CHANGE ** "

@dataclass()
class RemoveMarketData:
    SR_costs: pd.DataFrame
    risk_data: pd.DataFrame
    liquidity_data: pd.DataFrame

    min_volume_risk: float
    min_volume_contracts: int
    max_cost: float
    min_ann_perc_std: float

    existing_bad_markets: list

    @property
    def str_existing_markets_to_remove(self) -> str:
        return "Following should be removed (add to config.bad_markets): %s" % str(self.existing_markets_to_remove())

    def existing_markets_to_remove(self) -> list:
        existing_bad_markets = self.existing_bad_markets
        bad_markets = self.bad_markets()

        new_bad_markets = list(set(bad_markets).difference(set(existing_bad_markets)))

        return new_bad_markets

    @property
    def str_removed_markets_addback(self) -> str:
        return "Following should be removed (add to config.bad_markets): %s" % str(self.removed_markets_addback())

    def removed_markets_addback(self) -> list:
        existing_bad_markets = self.existing_bad_markets
        bad_markets = self.bad_markets()

        removed_bad_markets = list(set(existing_bad_markets).difference(set(bad_markets)))

        return removed_bad_markets

    def bad_markets(self) -> list:
        expensive = self.expensive_markets()
        not_enough_trading_risk = self.markets_without_enough_volume_contracts()
        not_enough_trading_contracts = self.markets_without_enough_volume_contracts()
        too_safe = self.too_safe_markets()

        bad_markets = list(set(expensive
                               + not_enough_trading_risk
                               + not_enough_trading_contracts
                               + too_safe))
        bad_markets.sort()

        return bad_markets

    @property
    def str_expensive_markets(self) -> str:
        return "Markets too expensive (%s): %s" % (
            self.reason_expensive_markets(),
            str(self.expensive_markets())
        )

    def reason_expensive_markets(self) -> str:
        return "SR cost per trade > %.3f" % self.max_cost

    def expensive_markets(self) -> list:
        SR_costs = self.SR_costs
        max_cost = self.max_cost
        expensive = list(SR_costs[SR_costs.SR_cost > max_cost].index)

        return expensive

    @property
    def str_markets_without_enough_volume_risk(self) -> str:
        return "Markets not enough risk volume (%s): %s" % (
            self.reason_markets_without_enough_volume_risk(),
            str(self.markets_without_enough_volume_risk())
        )


    def reason_markets_without_enough_volume_risk(self) -> str:
        return "Volume in $m ann. risk per day < %.2f" % self.min_volume_risk

    def markets_without_enough_volume_risk(self) -> list:
        min_volume_risk = self.min_volume_risk
        liquidity_data = self.liquidity_data
        not_enough_trading_risk = list(liquidity_data[liquidity_data.risk < min_volume_risk].index)

        return not_enough_trading_risk

    @property
    def str_markets_without_enough_volume_contracts(self) -> str:
        return "Markets not enough contract volume (%s): %s" % (
            self.reason_markets_without_enough_volume_contracts(),
            str(self.markets_without_enough_volume_contracts())
        )

    def reason_markets_without_enough_volume_contracts(self) -> str:
        return "Volume in contracts per day < %d" % int(self.min_volume_contracts)

    def markets_without_enough_volume_contracts(self) -> list:
        liquidity_data = self.liquidity_data
        min_contracts = self.min_volume_contracts
        not_enough_trading_contracts = list(
            liquidity_data[liquidity_data.contracts < min_contracts].index
        )

        return not_enough_trading_contracts

    @property
    def str_too_safe_markets(self) -> str:
        return "Markets too safe (%s): %s" % (
            self.reason_too_safe_markets(),
            str(self.too_safe_markets())
        )

    def reason_too_safe_markets(self) -> str:
        return "Annual %% std. dev < %.1f" % self.min_ann_perc_std

    def too_safe_markets(self) -> list:
        risk_data = self.risk_data
        min_ann_perc_std = self.min_ann_perc_std
        too_safe = list(risk_data[risk_data.annual_perc_stdev < min_ann_perc_std].index)

        return too_safe


def get_remove_market_data(data) -> RemoveMarketData:
    existing_bad_markets = get_existing_bad_markets()

    max_cost, min_volume_contracts, min_volume_risk, \
             = get_bad_market_filter_parameters()

    auto_parameters = get_auto_population_parameters()
    min_ann_perc_std = from_auto_parameters_to_min_ann_perc_std(auto_parameters)
    SR_costs, liquidity_data, risk_data = get_data_for_markets(data)


    return RemoveMarketData(
        SR_costs = SR_costs,
        liquidity_data = liquidity_data,
        risk_data = risk_data,
        min_ann_perc_std = min_ann_perc_std,
        max_cost = max_cost,
        min_volume_risk=min_volume_risk,
        min_volume_contracts=min_volume_contracts,
        existing_bad_markets=existing_bad_markets



        )

def get_list_of_duplicate_market_tables(data):
    filters = get_bad_market_filter_parameters()
    duplicate_dict = generate_matching_duplicate_dict()
    mkt_data = get_data_for_markets(data)
    duplicates = [
        table_of_duplicate_markets_for_dict_entry(mkt_data, dict_entry, filters)
        for dict_entry in duplicate_dict.values()
    ]

    return duplicates

def text_suggest_changes_to_duplicate_markets(list_of_duplicate_market_tables: list) -> str:
    suggest_changes = [
        dup_table.Heading for dup_table in
        list_of_duplicate_market_tables
        if CHANGE_FLAG in dup_table.Heading

    ]
    if len(suggest_changes)==0:
        return "No changes to duplicate markets required"

    suggest_changes = "\n".join(suggest_changes)

    return suggest_changes


@dataclass()
class parametersForAutoPopulation:
    raw_max_leverage: float
    max_vs_average_forecast: float
    notional_risk_target: float
    approx_IDM: float
    notional_instrument_weight: float

from sysproduction.reporting.data.constants import RISK_TARGET_ASSUMED, IDM_ASSUMED, MAX_VS_AVERAGE_FORECAST, INSTRUMENT_WEIGHT_ASSUMED, RAW_MAX_LEVERAGE

def get_auto_population_parameters() -> parametersForAutoPopulation:
    notional_risk_target = RISK_TARGET_ASSUMED/100.0
    approx_IDM = IDM_ASSUMED
    notional_instrument_weight= INSTRUMENT_WEIGHT_ASSUMED
    raw_max_leverage= RAW_MAX_LEVERAGE
    max_vs_average_forecast = MAX_VS_AVERAGE_FORECAST

    # because we multiply by eg 2, need to half this
    auto_parameters = parametersForAutoPopulation(raw_max_leverage = raw_max_leverage,
                   max_vs_average_forecast = max_vs_average_forecast,
                   notional_risk_target =notional_risk_target,
                   approx_IDM = approx_IDM,
                   notional_instrument_weight = notional_instrument_weight)

    return auto_parameters



def from_auto_parameters_to_min_ann_perc_std(auto_parameters: parametersForAutoPopulation) -> float:
    return 100*auto_parameters.max_vs_average_forecast *         \
            auto_parameters.approx_IDM *                     \
            auto_parameters.notional_instrument_weight *     \
            auto_parameters.notional_risk_target /           \
            auto_parameters.raw_max_leverage



def get_data_for_markets(data):
    SR_costs = get_table_of_SR_costs(data)
    SR_costs = SR_costs.dropna()
    liquidity_data = get_liquidity_data_df(data)
    risk_data = get_instrument_risk_table(data, only_held_instruments=False)

    return SR_costs, liquidity_data, risk_data




def get_existing_bad_markets():
    production_config = get_production_config()

    config = production_config.get_element_or_missing_data("exclude_instrument_lists")
    if config is missing_data:
        print("NO BAD MARKETS IN CONFIG!")
        existing_bad_markets = []
    else:
        existing_bad_markets = config['bad_markets']

    return existing_bad_markets




def table_of_duplicate_markets_for_dict_entry(
    mkt_data, dict_entry: dict, filters: tuple
):
    included = dict_entry["included"]
    excluded = dict_entry["excluded"]

    all_markets = list(set(list(included + excluded)))
    mkt_data_for_duplicates = get_df_of_data_for_duplicate(mkt_data, all_markets)
    best_market = get_best_market(mkt_data_for_duplicates, filters)
    current_list ="Current list of included markets %s, excluded markets %s"\
        % (included, excluded)

    suggested_list =\
        "Best market %s, current included market(s) %s" % (best_market, str(included))


    if best_market is no_good_markets:
        change_str = "No change - no good markets"

    elif len(included) > 1:
        change_str = "%s Replace %s with %s" % (CHANGE_FLAG,
                                                str(included),
                                                best_market)

    elif best_market != included[0]:
        change_str = "%s Replace %s with %s" % (CHANGE_FLAG,
                                                included[0],
                                                best_market)
    else:
        change_str = "No change required"

    all_string = change_str+ " "+ current_list + " " + suggested_list

    return table(Heading=all_string,
                 Body = mkt_data_for_duplicates)


def get_df_of_data_for_duplicate(mkt_data, all_markets: list) -> pd.DataFrame:
    mkt_data_for_duplicates = [
        get_market_data_for_duplicate(mkt_data, instrument_code)
        for instrument_code in all_markets
    ]

    mkt_data_for_duplicates = pd.DataFrame(mkt_data_for_duplicates, index=all_markets)

    return mkt_data_for_duplicates


no_good_markets = named_object("<No good markets>")


def get_best_market(mkt_data_for_duplicates: pd.DataFrame, filters: tuple) -> str:
    max_cost, min_contracts, min_risk = filters
    only_valid = mkt_data_for_duplicates.dropna()
    only_valid = only_valid[only_valid.SR_cost <= max_cost]
    only_valid = only_valid[only_valid.volume_contracts > min_contracts]
    only_valid = only_valid[only_valid.volume_risk > min_risk]

    if len(only_valid) == 0:
        return no_good_markets

    only_valid = only_valid.sort_values("contract_size")
    best_market = only_valid.index[0]
    return best_market


def get_market_data_for_duplicate(mkt_data, instrument_code: str):
    SR_costs, liquidity_data, risk_data = mkt_data
    SR_cost = SR_costs.SR_cost.get(instrument_code, np.nan)
    volume_contracts = liquidity_data.contracts.get(instrument_code, np.nan)
    volume_risk = liquidity_data.risk.get(instrument_code, np.nan)
    contract_size = risk_data.annual_risk_per_contract.get(instrument_code, np.nan)

    return dict(
        SR_cost=np.round(SR_cost, 6),
        volume_contracts=volume_contracts,
        volume_risk=np.round(volume_risk, 2),
        contract_size=np.round(contract_size),
    )




def get_bad_market_filter_parameters():
    max_cost = MAX_SR_COST
    min_contracts = MIN_VOLUME_CONTRACTS_DAILY
    min_risk = MIN_VOLUME_RISK_DAILY

    return max_cost, min_contracts, min_risk