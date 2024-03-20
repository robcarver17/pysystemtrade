from typing import List

import pandas as pd
import numpy as np

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
    configured = get_current_configured_block_costs(data)
    list_of_instrument_codes = configured.index
    list_of_broker = get_broker_block_costs(data=data, list_of_instrument_codes=list_of_instrument_codes)
    both = pd.concat([configured, list_of_broker], axis=1)
    both.columns = [CONFIGURED_COLUMN, BROKER_COLUMN]
    return both

CONFIGURED_COLUMN = 'configured'
BROKER_COLUMN = 'broker'
RATIO_COLUMN = 'ratio'

def get_current_configured_block_costs(data: dataBlob) -> pd.Series:
    diag_instruments = diagInstruments(data)

    return diag_instruments.get_block_commissions_as_series()

def get_broker_block_costs(data: dataBlob, list_of_instrument_codes: List[str]) ->pd.Series:
    priced_contracts = get_series_of_priced_contracts(data=data, list_of_instrument_codes=list_of_instrument_codes)
    block_costs = get_costs_given_priced_contracts(data=data, priced_contracts=priced_contracts)
    return pd.Series(block_costs)

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

def get_costs_given_priced_contracts(data: dataBlob, priced_contracts: pd.Series)-> pd.Series:
    db = dataBroker(data)
    block_costs = {}
    for instrument_code, contract in priced_contracts.items():
        try:
            costs = db.get_commission_for_contract(contract)
        except:
            costs = np.nan
        block_costs[instrument_code] = costs
    return pd.Series(block_costs)
