import numpy as np
import pandas as pd
from dataclasses import dataclass

from syscore.constants import named_object, arg_not_supplied
from syscore.genutils import list_union
from sysdata.config.instruments import (
    generate_matching_duplicate_dict,
    get_list_of_ignored_instruments_in_config,
    get_list_of_bad_instruments_in_config,
)
from sysproduction.reporting.data.constants import (
    MAX_SR_COST,
    MIN_VOLUME_CONTRACTS_DAILY,
    MIN_VOLUME_RISK_DAILY,
    BAD_THRESHOLD,
)

from sysproduction.reporting.reporting_functions import table

from sysproduction.reporting.data.costs import (
    get_table_of_SR_costs,
)
from sysproduction.data.config import get_list_of_stale_instruments_given_config
from sysproduction.reporting.data.volume import get_liquidity_data_df
from sysproduction.reporting.data.risk import get_instrument_risk_table

CHANGE_FLAG = "** CHANGE ** "


@dataclass()
class parametersForAutoPopulation:
    raw_max_leverage: float
    max_vs_average_forecast: float
    notional_risk_target: float
    approx_IDM: float
    notional_instrument_weight: float


@dataclass()
class RemoveMarketData:
    SR_costs: pd.DataFrame
    risk_data: pd.DataFrame
    liquidity_data: pd.DataFrame

    min_volume_risk: float
    min_volume_contracts: int
    max_cost: float

    auto_parameters: parametersForAutoPopulation

    existing_bad_markets: list
    exclude_markets: list

    @property
    def str_existing_markets_to_remove(self) -> str:
        return (
            "Following should be removed from trading (add to config.bad_markets) [%f threshold]: %s "
            % (BAD_THRESHOLD, str(self.existing_markets_to_remove()))
        )

    def existing_markets_to_remove(self) -> list:
        existing_bad_markets = self.existing_bad_markets

        ## To be stopped from trading an existing market must be well below the threshold for not being a bad market
        bad_markets = self.bad_markets(apply_lower_threshold=True)

        new_bad_markets = list(set(bad_markets).difference(set(existing_bad_markets)))

        return new_bad_markets

    @property
    def str_removed_markets_addback(self) -> str:
        return (
            "Following should be allowed to trade (delete from config.bad_markets) [%f threshold]: %s"
            % (BAD_THRESHOLD, str(self.removed_markets_addback()))
        )

    @property
    def str_all_recommended_bad_markets_clean_slate_in_yaml_form(self) -> str:
        clean_slate_list_of_bad_markets = self.bad_markets(
            apply_higher_threshold=False, apply_lower_threshold=False
        )
        market_config_as_yaml_str = _yaml_bad_market_list(
            clean_slate_list_of_bad_markets
        )
        return (
            "Use the following if you want a clean slate without considering existing markets \n%s "
            % market_config_as_yaml_str
        )

    @property
    def str_all_recommended_bad_markets_in_yaml_form(self) -> str:
        recommended_list_of_bad_markets = self.recommended_list_of_bad_markets()
        market_config_as_yaml_str = _yaml_bad_market_list(
            recommended_list_of_bad_markets
        )
        return (
            "Use the following if you want to minimise turnover of markets\n%s "
            % market_config_as_yaml_str
        )

    def recommended_list_of_bad_markets(self):
        existing_bad_markets = self.existing_bad_markets
        to_be_removed = self.removed_markets_addback()
        new_bad_markets = self.existing_markets_to_remove()

        set_of_markets_without_removals = set(existing_bad_markets).difference(
            set(to_be_removed)
        )
        set_of_markets_without_removals_and_with_new_baddies = set(
            set_of_markets_without_removals
        ).union(set(new_bad_markets))
        recommended_list_of_bad = list(
            set_of_markets_without_removals_and_with_new_baddies
        )

        return recommended_list_of_bad

    def removed_markets_addback(self) -> list:
        existing_bad_markets = self.existing_bad_markets
        exclude_markets = self.exclude_markets

        ## To be allowed to trade an existing bad market must be well above the threshold for not being a bad market
        bad_markets = self.bad_markets(apply_higher_threshold=True)

        # Markets to be added back = (existing bad markets - new bad markets) - (ignored and stale instruments)
        removed_bad_markets = list(
            set(existing_bad_markets)
            .difference(set(bad_markets))
            .difference(set(exclude_markets))
        )

        return removed_bad_markets

    def bad_markets(
        self, apply_higher_threshold=False, apply_lower_threshold=False
    ) -> list:
        threshold_factor = calculate_threshold_factor(
            apply_lower_threshold=apply_lower_threshold,
            apply_higher_threshold=apply_higher_threshold,
        )

        expensive = self.expensive_markets(threshold_factor=threshold_factor)
        not_enough_trading_risk = self.markets_without_enough_volume_risk(
            threshold_factor=threshold_factor
        )
        not_enough_trading_contracts = self.markets_without_enough_volume_contracts(
            threshold_factor=threshold_factor
        )
        too_safe = self.too_safe_markets(threshold_factor=threshold_factor)

        bad_markets = list(
            set(
                expensive
                + not_enough_trading_risk
                + not_enough_trading_contracts
                + too_safe
            )
        )
        bad_markets = list(set(bad_markets))
        bad_markets.sort()

        return bad_markets

    @property
    def str_expensive_markets(self) -> str:
        return "Markets too expensive (%s): %s" % (
            self.reason_expensive_markets(),
            str(self.expensive_markets()),
        )

    def reason_expensive_markets(self) -> str:
        return "SR cost per trade > %.3f" % self.max_cost

    def expensive_markets(self, threshold_factor: float = 1.0) -> list:
        ## Threshold
        ## If larger than 1, applied higher threshold: it will be easier to be a bad market, harder not to be
        ## If less than 1, applied lower threshold: it will be harder to be a bad market, easier not to be

        ## Lower maximum cost means easier to be a bad market

        SR_costs = self.SR_costs
        max_cost = self.max_cost / threshold_factor
        expensive = list(SR_costs[SR_costs.SR_cost > max_cost].index)
        expensive.sort()

        return expensive

    @property
    def str_markets_without_enough_volume_risk(self) -> str:
        return "Markets not enough risk volume (%s): %s" % (
            self.reason_markets_without_enough_volume_risk(),
            str(self.markets_without_enough_volume_risk()),
        )

    def reason_markets_without_enough_volume_risk(self) -> str:
        return "Volume in $m ann. risk per day < %.2f" % self.min_volume_risk

    def markets_without_enough_volume_risk(self, threshold_factor: float = 1.0) -> list:
        ## Threshold
        ## If larger than 1, applied higher threshold: it will be easier to be a bad market, harder not to be
        ## If less than 1, applied lower threshold: it will be harder to be a bad market, easier not to be

        ## Higher min_volume_risk means it is easier to be a bad market

        min_volume_risk = self.min_volume_risk * threshold_factor
        liquidity_data = self.liquidity_data
        not_enough_trading_risk = list(
            liquidity_data[liquidity_data.risk < min_volume_risk].index
        )
        not_enough_trading_risk.sort()

        return not_enough_trading_risk

    @property
    def str_markets_without_enough_volume_contracts(self) -> str:
        return "Markets not enough contract volume (%s): %s" % (
            self.reason_markets_without_enough_volume_contracts(),
            str(self.markets_without_enough_volume_contracts()),
        )

    def reason_markets_without_enough_volume_contracts(self) -> str:
        return "Volume in contracts per day < %d" % int(self.min_volume_contracts)

    def markets_without_enough_volume_contracts(
        self, threshold_factor: float = 1.0
    ) -> list:
        ## Threshold
        ## If larger than 1, applied higher threshold: it will be easier to be a bad market, harder not to be
        ## If less than 1, applied lower threshold: it will be harder to be a bad market, easier not to be

        ## Higher min_contracts means it is easier to be a bad market

        liquidity_data = self.liquidity_data
        min_contracts = self.min_volume_contracts * threshold_factor
        not_enough_trading_contracts = list(
            liquidity_data[liquidity_data.contracts < min_contracts].index
        )
        not_enough_trading_contracts.sort()

        return not_enough_trading_contracts

    @property
    def str_too_safe_markets(self) -> str:
        return "Markets too safe (%s): %s" % (
            self.reason_too_safe_markets(),
            str(self.too_safe_markets()),
        )

    def reason_too_safe_markets(self) -> str:
        return "Annual %% std. dev < %.1f" % self.min_ann_perc_std

    def too_safe_markets(self, threshold_factor: float = 1.0) -> list:
        ## Threshold
        ## If larger than 1, applied higher threshold: it will be easier to be a bad market, harder not to be
        ## If less than 1, applied lower threshold: it will be harder to be a bad market, easier not to be

        ## Higher min_ann_perc_std means it is easier to be a bad market

        risk_data = self.risk_data
        min_ann_perc_std = self.min_ann_perc_std * threshold_factor
        too_safe = list(risk_data[risk_data.annual_perc_stdev < min_ann_perc_std].index)
        too_safe.sort()

        return too_safe

    @property
    def str_explain_safety(self) -> str:
        auto_parameters = self.auto_parameters
        str1 = (
            "(Minimum standard deviation %.3f calculated as follows: "
            % self.min_ann_perc_std
        )
        str2 = "= max_vs_average_forecast * approx_IDM * notional_instrument_weight * notional_risk_target /  raw_max_leverage"
        str3 = "= %.1f * %.2f * %.3f * %.3f / %2f" % (
            auto_parameters.max_vs_average_forecast,
            auto_parameters.approx_IDM,
            auto_parameters.notional_instrument_weight,
            auto_parameters.notional_risk_target,
            auto_parameters.raw_max_leverage,
        )

        return str1 + str2 + str3

    @property
    def min_ann_perc_std(self) -> float:
        min_ann_perc_std = from_auto_parameters_to_min_ann_perc_std(
            self.auto_parameters
        )
        return min_ann_perc_std


def _yaml_bad_market_list(list_of_bad_markets: list) -> str:
    list_of_bad_markets.sort()
    list_in_yaml_form = [
        "    - %s \n" % instrument_code for instrument_code in list_of_bad_markets
    ]
    yaml_string = "".join(list_in_yaml_form)

    return (
        "Put following into config.yaml\nexclude_instrument_lists:\n  bad_markets:\n%s"
        % yaml_string
    )


def get_remove_market_data(data) -> RemoveMarketData:
    (
        max_cost,
        min_volume_contracts,
        min_volume_risk,
    ) = get_bad_market_filter_parameters()

    auto_parameters = get_auto_population_parameters()

    existing_bad_markets = get_list_of_bad_markets(data)

    ignored_instruments = get_ignored_instruments(data)
    stale_instruments = get_stale_instruments(data)
    exclude_instruments = list_union(ignored_instruments, stale_instruments)

    SR_costs, liquidity_data, risk_data = get_data_for_markets(
        data, exclude_instruments=exclude_instruments
    )

    return RemoveMarketData(
        SR_costs=SR_costs,
        liquidity_data=liquidity_data,
        risk_data=risk_data,
        max_cost=max_cost,
        min_volume_risk=min_volume_risk,
        min_volume_contracts=min_volume_contracts,
        existing_bad_markets=existing_bad_markets,
        auto_parameters=auto_parameters,
        exclude_markets=exclude_instruments,
    )


def get_list_of_duplicate_market_tables(data):
    filters = get_bad_market_filter_parameters()
    duplicate_dict = generate_matching_duplicate_dict(config=data.config)
    mkt_data = get_data_for_markets(data)
    duplicates = [
        table_of_duplicate_markets_for_dict_entry(mkt_data, dict_entry, filters)
        for dict_entry in duplicate_dict.values()
    ]

    return duplicates


def text_suggest_changes_to_duplicate_markets(
    list_of_duplicate_market_tables: list,
) -> str:
    suggest_changes = [
        dup_table.Heading
        for dup_table in list_of_duplicate_market_tables
        if CHANGE_FLAG in dup_table.Heading
    ]
    if len(suggest_changes) == 0:
        return "No changes to duplicate markets required"

    suggest_changes = "\n".join(suggest_changes)

    return suggest_changes


from sysproduction.reporting.data.constants import (
    RISK_TARGET_ASSUMED,
    IDM_ASSUMED,
    MAX_VS_AVERAGE_FORECAST,
    INSTRUMENT_WEIGHT_ASSUMED,
    RAW_MAX_LEVERAGE,
)


def get_auto_population_parameters() -> parametersForAutoPopulation:
    notional_risk_target = RISK_TARGET_ASSUMED / 100.0
    approx_IDM = IDM_ASSUMED
    notional_instrument_weight = INSTRUMENT_WEIGHT_ASSUMED
    raw_max_leverage = RAW_MAX_LEVERAGE
    max_vs_average_forecast = MAX_VS_AVERAGE_FORECAST

    # because we multiply by eg 2, need to half this
    auto_parameters = parametersForAutoPopulation(
        raw_max_leverage=raw_max_leverage,
        max_vs_average_forecast=max_vs_average_forecast,
        notional_risk_target=notional_risk_target,
        approx_IDM=approx_IDM,
        notional_instrument_weight=notional_instrument_weight,
    )

    return auto_parameters


def from_auto_parameters_to_min_ann_perc_std(
    auto_parameters: parametersForAutoPopulation,
) -> float:
    return (
        100
        * auto_parameters.max_vs_average_forecast
        * auto_parameters.approx_IDM
        * auto_parameters.notional_instrument_weight
        * auto_parameters.notional_risk_target
        / auto_parameters.raw_max_leverage
    )


def get_data_for_markets(data, exclude_instruments: list = arg_not_supplied):
    SR_costs = get_table_of_SR_costs(data, exclude_instruments=exclude_instruments)
    SR_costs = SR_costs.dropna()
    liquidity_data = get_liquidity_data_df(
        data, exclude_instruments=exclude_instruments
    )
    risk_data = get_instrument_risk_table(
        data, only_held_instruments=False, exclude_instruments=exclude_instruments
    )

    return SR_costs, liquidity_data, risk_data


def get_ignored_instruments(data) -> list:
    production_config = data.config
    ignored_instruments = get_list_of_ignored_instruments_in_config(production_config)

    return ignored_instruments


def get_stale_instruments(data) -> list:
    production_config = data.config
    stale_instruments = get_list_of_stale_instruments_given_config(production_config)

    return stale_instruments


def get_list_of_bad_markets(data):
    production_config = data.config
    bad_markets = get_list_of_bad_instruments_in_config(production_config)

    return bad_markets


def table_of_duplicate_markets_for_dict_entry(
    mkt_data, dict_entry: dict, filters: tuple
):
    included = dict_entry["included"]
    excluded = dict_entry["excluded"]

    all_markets = list(set(list(included + excluded)))
    mkt_data_for_duplicates = get_df_of_data_for_duplicate(mkt_data, all_markets)
    best_market = get_best_market(mkt_data_for_duplicates, filters)
    current_list = "Current list of included markets %s, excluded markets %s" % (
        included,
        excluded,
    )

    suggested_list = "Best market %s, current included market(s) %s" % (
        best_market,
        str(included),
    )

    if best_market is no_good_markets:
        change_str = "No change - no good markets"

    elif len(included) > 1:
        change_str = "%s Replace %s with %s" % (CHANGE_FLAG, str(included), best_market)

    elif best_market != included[0]:
        change_str = "%s Replace %s with %s" % (CHANGE_FLAG, included[0], best_market)
    else:
        change_str = "No change required"

    all_string = change_str + " " + current_list + " " + suggested_list

    return table(Heading=all_string, Body=mkt_data_for_duplicates)


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


def calculate_threshold_factor(
    apply_lower_threshold: bool = False, apply_higher_threshold: bool = False
) -> float:
    ## The threshold factor is a number we apply
    ## To be stopped from trading an existing market must be well below the threshold for not being a bad market
    ## To be added to trading an existing bad market must be well above the threshold for not being a bad market

    ## We return a number
    ## If larger than 1, applied higher threshold: it will be easier to be a bad market, harder not to be
    ## If less than 1, applied lower threshold: it will be harder to be a bad market, easier not to be

    if apply_higher_threshold:
        if apply_lower_threshold:
            raise Exception("Can't apply both thresholds together")
        else:
            return 1 + BAD_THRESHOLD

    if apply_lower_threshold:
        if apply_higher_threshold:
            raise Exception("Can't apply both thresholds together")
        else:
            return 1 - BAD_THRESHOLD

    return 1.0
