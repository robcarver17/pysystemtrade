import numpy as np
import pandas as pd
from dataclasses import dataclass

from syscore.interactive import get_and_convert
from syscore.objects import missing_data, named_object
from sysdata.config.instruments import generate_matching_duplicate_dict
from sysdata.config.production_config import get_production_config
from sysdata.data_blob import dataBlob

from sysproduction.reporting.reporting_functions import table

from sysproduction.reporting.data.costs import (
    get_table_of_SR_costs,
)
from sysproduction.reporting.data.volume import get_liquidity_data_df
from sysproduction.reporting.data.risk import (
    get_instrument_risk_table)



MAX_SR_COST = 0.01
MIN_CONTRACTS_PER_DAY = 100
MIN_RISK = 1.5

CHANGE_FLAG = "** CHANGE ** "



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

MAX_VS_AVERAGE_FORECAST=2

def get_auto_population_parameters() -> parametersForAutoPopulation:
    print("Enter parameters to estimate typical position sizes")
    notional_risk_target = get_and_convert(
        "Notional risk target (% per year)", type_expected=float, default_value=0.25
    )
    approx_IDM = get_and_convert(
        "Approximate IDM", type_expected=float, default_value=2.5
    )
    notional_instrument_weight = get_and_convert(
        "Notional instrument weight (go large for safety!)",
        type_expected=float,
        default_value=0.1,
    )
    raw_max_leverage = get_and_convert(
        "Maximum Leverage per instrument (notional exposure*# contracts / capital)",
        type_expected=float,
        default_value=1.0,
    )
    # because we multiply by eg 2, need to half this
    auto_parameters = parametersForAutoPopulation(raw_max_leverage = raw_max_leverage,
                   max_vs_average_forecast = MAX_VS_AVERAGE_FORECAST,
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


def print_and_return_entire_bad_market_list(    SR_costs: pd.DataFrame,
    liquidity_data: pd.DataFrame,
    risk_data: pd.DataFrame,
    max_cost: float = 0.01,
    min_risk: float = 1.5,
    min_contracts: int = 100,
    min_ann_perc_std = 1.25
    ) -> list:

    expensive, not_enough_trading_risk, \
    too_safe, not_enough_trading_contracts =\
        get_bad_market_list(SR_costs=SR_costs,
                            liquidity_data=liquidity_data,
                            risk_data=risk_data,
                            max_cost=max_cost,
                            min_risk=min_risk,
                            min_contracts=min_contracts,
                            min_ann_perc_std=min_ann_perc_std)

    print("Too expensive: (SR cost> %.2f)\n" % max_cost)
    print(expensive)
    print("\n Too safe: (Annual risk< %.2f) \n" % min_ann_perc_std)
    print(too_safe)
    print("\n Not enough volume (contracts < %d):  \n" % int(min_contracts))
    print(not_enough_trading_contracts)
    print("\n Not enough volume (risk < %.2f): \n" % min_risk)
    print(not_enough_trading_risk)

    bad_markets = list(set(expensive
                           + not_enough_trading_risk
                           + not_enough_trading_contracts
                           + too_safe))
    bad_markets.sort()

    return bad_markets


def get_bad_market_list(
    SR_costs: pd.DataFrame,
    liquidity_data: pd.DataFrame,
    risk_data: pd.DataFrame,
    max_cost: float = 0.01,
    min_risk: float = 1.5,
    min_contracts: int = 100,
    min_ann_perc_std = 1.25
) -> tuple:
    expensive = list(SR_costs[SR_costs.SR_cost > max_cost].index)

    not_enough_trading_contracts = list(
        liquidity_data[liquidity_data.contracts < min_contracts].index
    )
    not_enough_trading_risk = list(liquidity_data[liquidity_data.risk < min_risk].index)

    too_safe = list(risk_data[risk_data.annual_perc_stdev<min_ann_perc_std].index)

    too_safe.sort()
    expensive.sort()
    not_enough_trading_contracts.sort()
    not_enough_trading_risk.sort()

    return expensive, not_enough_trading_risk, too_safe, not_enough_trading_contracts


def display_bad_market_info(bad_markets: list):

    existing_bad_markets = get_existing_bad_markets()
    existing_bad_markets.sort()

    new_bad_markets = list(set(bad_markets).difference(set(existing_bad_markets)))
    removed_bad_markets = list(set(existing_bad_markets).difference(set(bad_markets)))

    print("New bad markets %s" % new_bad_markets)
    print("Removed bad markets %s" % removed_bad_markets)

    print("Add the following to yaml .config under bad_markets heading:\n")
    print("bad_markets:")
    __ = [print("  - %s" % instrument) for instrument in bad_markets]


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


def suggest_bad_markets(data: dataBlob):
    max_cost, min_contracts, min_risk, \
             = get_bad_market_filter_parameters()

    auto_parameters = get_auto_population_parameters()
    min_ann_perc_std = from_auto_parameters_to_min_ann_perc_std(auto_parameters)
    SR_costs, liquidity_data, risk_data = get_data_for_markets(data)
    bad_markets = print_and_return_entire_bad_market_list(
        SR_costs=SR_costs,
        liquidity_data=liquidity_data,
        risk_data =risk_data,
        min_risk=min_risk,
        min_contracts=min_contracts,
        max_cost=max_cost,
        min_ann_perc_std=min_ann_perc_std
    )
    display_bad_market_info(bad_markets)


def get_bad_market_filter_parameters():
    max_cost = MAX_SR_COST
    min_contracts = MIN_CONTRACTS_PER_DAY
    min_risk = MIN_RISK

    return max_cost, min_contracts, min_risk