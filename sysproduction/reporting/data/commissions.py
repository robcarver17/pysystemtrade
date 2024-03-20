from typing import List, Dict

import pandas as pd
import numpy as np
from syscore.genutils import list_intersection
from sysobjects.spot_fx_prices import currencyValue
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.broker import dataBroker
from sysproduction.data.contracts import dataContracts
from sysobjects.contracts import futuresContract
from sysdata.data_blob import dataBlob

def df_of_configure_and_broker_block_cost_with_ratio_sorted(data: dataBlob) -> pd.DataFrame:
    df = df_of_configure_and_broker_block_cost(data)
    diff = df[BROKER_COLUMN] - df[CONFIGURED_COLUMN]
    df[RATIO_COLUMN] = ratio

    df.sort_values(by=RATIO_COLUMN)

    return df

def df_of_configure_and_broker_block_cost(data: dataBlob) -> pd.DataFrame:
    list_of_instrument_codes = get_instrument_list(data)

    configured_costs = get_current_configured_block_costs(data=data, list_of_instrument_codes=list_of_instrument_codes)
    broker_costs = get_broker_block_costs(data=data, list_of_instrument_codes=list_of_instrument_codes)

    both = []
    for instrument_code in list_of_instrument_codes:
        configured_cost = configured_costs[instrument_code]
        broker_cost = broker_costs[instrument_code]

        if configured_cost.currency==broker_cost.currency:
            both.append([configured_cost.value, broker_cost.value])

    both = pd.DataFrame(both)
    both.columns = [CONFIGURED_COLUMN, BROKER_COLUMN]
    return both

CONFIGURED_COLUMN = 'configured'
BROKER_COLUMN = 'broker'
RATIO_COLUMN = 'ratio'

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
            costs = np.nan
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
            costs = np.nan
        block_costs_from_broker[instrument_code] = costs
    return block_costs_from_broker
