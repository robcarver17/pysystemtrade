import pandas as pd
from sysdata.data_blob import dataBlob
from sysdata.mongodb.mongo_positions_by_strategy_TO_DEPRECATE import (
    mongoStrategyPositionData,
)
from sysdata.mongodb.mongo_position_by_contract_TO_DEPRECATE import (
    mongoContractPositionData,
)
from sysdata.arctic.arctic_historic_strategy_positions import arcticStrategyPositionData
from sysdata.arctic.arctic_historic_contract_positions import arcticContractPositionData


def from_list_of_entries_to_pd_series(list_of_entries: list, keyname: str):
    date_index = [item["date"] for item in list_of_entries]
    data_list = [item[keyname] for item in list_of_entries]

    return pd.Series(data_list, index=date_index)


def update_strategy_positions():
    data = dataBlob(keep_original_prefix=True)
    data.add_class_list([mongoStrategyPositionData, arcticStrategyPositionData])

    list_of_instrument_strategies = (
        data.mongo_strategy_position.get_list_of_instrument_strategies()
    )

    for instrument_strategy in list_of_instrument_strategies:
        old_data = (
            data.mongo_strategy_position.mongo_data.get_result_dict_for_dict_keys(
                instrument_strategy.as_dict()
            )
        )
        list_of_entries = old_data["entry_series"]
        data_as_series = from_list_of_entries_to_pd_series(list_of_entries, "position")
        data.arctic_strategy_position._write_updated_position_series_for_instrument_strategy_object(
            instrument_strategy, data_as_series
        )


def update_contract_positions():
    data = dataBlob(keep_original_prefix=True)
    data.add_class_list([mongoContractPositionData, arcticContractPositionData])

    list_of_contracts = data.mongo_contract_position.get_list_of_contracts()

    for contract in list_of_contracts:
        contractid = "%s.%s" % (contract.instrument_code, contract.contract_date)
        old_data = (
            data.mongo_contract_position.mongo_data.get_result_dict_for_dict_keys(
                dict(contractid=contractid)
            )
        )
        list_of_entries = old_data["entry_series"]
        data_as_series = from_list_of_entries_to_pd_series(list_of_entries, "position")
        data.arctic_contract_position._write_updated_position_series_for_contract_object(
            contract_object=contract, updated_series=data_as_series
        )
