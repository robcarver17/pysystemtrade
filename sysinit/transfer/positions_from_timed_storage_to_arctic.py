import pandas as pd
from sysdata.mongodb.mongo_positions_by_strategy_TO_DEPRECATE import (
    mongoStrategyPositionData,
)
from sysdata.mongodb.mongo_position_by_contract_TO_DEPRECATE import (
    mongoContractPositionData,
)
from sysdata.mongodb.mongo_optimal_position_TO_DEPRECATE import mongoOptimalPositionData

from sysdata.arctic.arctic_historic_strategy_positions import arcticStrategyPositionData
from sysdata.arctic.arctic_historic_contract_positions import arcticContractPositionData
from sysdata.arctic.arctic_optimal_positions import arcticOptimalPositionData

from syslogdiag.log_to_screen import logtoscreen
from sysobjects.production.tradeable_object import instrumentStrategy
from sysobjects.contracts import futuresContract


def from_list_of_entries_to_pd_series(list_of_entries: list, keyname: str):
    date_index = [item["date"] for item in list_of_entries]
    data_list = [item[keyname] for item in list_of_entries]

    return pd.Series(data_list, index=date_index)


def transfer_strategy_positions():
    old_data = mongoStrategyPositionData()
    new_data = arcticStrategyPositionData()

    list_of_instrument_strategies = [
        instrumentStrategy(
            instrument_code=result_dict["instrument_code"],
            strategy_name=result_dict["strategy_name"],
        )
        for result_dict in old_data.mongo_data.get_list_of_all_dicts()
    ]

    for instrument_strategy in list_of_instrument_strategies:
        old_data_for_instrument_strategy = (
            old_data.mongo_data.get_result_dict_for_dict_keys(
                instrument_strategy.as_dict()
            )
        )
        list_of_entries = old_data_for_instrument_strategy["entry_series"]
        data_as_series = from_list_of_entries_to_pd_series(list_of_entries, "position")
        new_data._write_updated_position_series_for_instrument_strategy_object(
            instrument_strategy, data_as_series
        )


def transfer_contract_positions():
    old_data = mongoContractPositionData()
    new_data = arcticContractPositionData()

    def _create_contract(result_dict):
        list_of_ident = result_dict["contractid"].split(".")
        return futuresContract(
            instrument_object=list_of_ident[0], contract_date_object=list_of_ident[1]
        )

    list_of_contracts = [
        _create_contract(result_dict)
        for result_dict in old_data.mongo_data.get_list_of_all_dicts()
    ]

    for contract in list_of_contracts:
        contractid = "%s.%s" % (contract.instrument_code, contract.contract_date)
        old_data_for_contract = old_data.mongo_data.get_result_dict_for_dict_keys(
            dict(contractid=contractid)
        )
        list_of_entries = old_data_for_contract["entry_series"]
        data_as_series = from_list_of_entries_to_pd_series(list_of_entries, "position")
        new_data._write_updated_position_series_for_contract_object(
            contract_object=contract, updated_series=data_as_series
        )


def transfer_optimal_positions():
    old_data = mongoOptimalPositionData()
    new_data = arcticOptimalPositionData()

    all_dicts = old_data.mongo_data.get_list_of_all_dicts()

    for item_in_list in all_dicts:
        instrument_strategy = instrumentStrategy(
            item_in_list["strategy_name"], item_in_list["instrument_code"]
        )
        ## not supported
        if instrument_strategy.strategy_name == "mr":
            continue
        entry_series = item_in_list["entry_series"]
        as_df = pd.DataFrame(entry_series)
        date_index = as_df.date
        as_df = as_df.drop("date", axis=1)
        as_df.index = date_index

        new_data.write_optimal_position_as_df_for_instrument_strategy_without_checking(
            instrument_strategy=instrument_strategy, optimal_positions_as_df=as_df
        )
