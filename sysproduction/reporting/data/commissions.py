from typing import List, Dict

import pandas as pd
import numpy as np
from sysobjects.spot_fx_prices import currencyValue
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.broker import dataBroker
from sysproduction.data.contracts import dataContracts
from sysobjects.contracts import futuresContract
from sysdata.data_blob import dataBlob

missing = currencyValue(currency='missing', value=0)


def df_of_configure_and_broker_block_cost_sorted_by_diff(data: dataBlob) -> pd.DataFrame:
    list_of_instrument_codes = get_instrument_list(data)

    configured_costs = get_current_configured_block_costs(data=data, list_of_instrument_codes=list_of_instrument_codes)
    broker_costs = get_broker_block_costs(data=data, list_of_instrument_codes=list_of_instrument_codes)

    valid_costs = {}
    missing_values = {}
    for instrument_code in list_of_instrument_codes:
        update_valid_and_missing_costs_for_instrument_code(instrument_code=instrument_code,
                                                           missing_values=missing_values,
                                                           valid_costs=valid_costs,
                                                           broker_costs=broker_costs,
                                                           configured_costs=configured_costs)

    valid_costs_df = create_df_in_commission_report(valid_costs)
    missing_values_df = create_df_in_commission_report(missing_values)

    both = pd.concat([valid_costs_df, missing_values_df], axis=0)

    return both

def update_valid_and_missing_costs_for_instrument_code(instrument_code: str,
                                                       configured_costs: Dict[str, currencyValue],
                                                       broker_costs: dict[str, currencyValue],
                                                    valid_costs: dict, missing_values: dict):
    configured_cost = configured_costs.get(instrument_code, missing)
    broker_cost = broker_costs.get(instrument_code, missing)

    if configured_cost is missing or broker_cost is missing:
        missing_values[instrument_code] = [configured_cost.currency, broker_cost.currency, "One or both missing"]
    elif configured_cost.currency == broker_cost.currency:
        configured_cost_instrument = configured_cost.value
        broker_cost_instrument = broker_cost.value
        diff = broker_cost_instrument - configured_cost_instrument
        valid_costs[instrument_code] = [configured_cost_instrument, broker_cost_instrument, diff]
    else:
        missing_values[instrument_code] = [configured_cost.currency, broker_cost.currency, "Currency doesn't match"]

def create_df_in_commission_report(some_dict: dict):
    some_df = pd.DataFrame(some_dict)
    some_df = some_df.transpose()
    some_df.columns =  [CONFIGURED_COLUMN, BROKER_COLUMN, DIFF_COLUMN]
    some_df = some_df.sort_values(DIFF_COLUMN, ascending=False)

    return some_df

CONFIGURED_COLUMN = 'configured'
BROKER_COLUMN = 'broker'
DIFF_COLUMN = 'diff'

def get_instrument_list(data: dataBlob)-> list:
    db = dataBroker(data)
    list_of_instruments = db.broker_futures_contract_price_data.get_list_of_instrument_codes_with_merged_price_data()

    return list_of_instruments

def get_current_configured_block_costs(data: dataBlob, list_of_instrument_codes: List[str]) -> Dict[str, currencyValue]:
    diag_instruments = diagInstruments(data)
    block_costs_from_config = {}
    for instrument_code in list_of_instrument_codes:
        try:
            costs = diag_instruments.get_block_commission_for_instrument_as_currency_value(instrument_code)
        except:
            costs = missing
        block_costs_from_config[instrument_code] = costs

    return block_costs_from_config

def get_broker_block_costs(data: dataBlob, list_of_instrument_codes: List[str]) -> Dict[str, currencyValue]:
    priced_contracts = get_series_of_priced_contracts(data=data, list_of_instrument_codes=list_of_instrument_codes)
    block_costs_from_broker = get_costs_given_priced_contracts(data=data, priced_contracts=priced_contracts)
    return block_costs_from_broker

def get_series_of_priced_contracts(data: dataBlob, list_of_instrument_codes: List[str]) -> pd.Series:
    dc = dataContracts(data)
    list_of_priced_contracts = {}
    for instrument_code in list_of_instrument_codes:
        try:
            contract = futuresContract(instrument_code, dc.get_priced_contract_id(instrument_code))
        except:
            continue
        list_of_priced_contracts[instrument_code] = contract
    return pd.Series(list_of_priced_contracts)

def get_costs_given_priced_contracts(data: dataBlob, priced_contracts: pd.Series) -> Dict[str, currencyValue]:
    db = dataBroker(data)
    block_costs_from_broker = {}
    for instrument_code, contract in priced_contracts.items():
        try:
            costs = db.get_commission_for_contract_in_currency_value(contract)
        except:
            costs = missing
        block_costs_from_broker[instrument_code] = costs
    return block_costs_from_broker

