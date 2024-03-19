from typing import List

import pandas as pd
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.broker import dataBroker
from sysproduction.data.contracts import dataContracts
from sysobjects.contracts import futuresContract

def df_of_configure_and_broker_block_cost(data) -> pd.DataFrame:
    configured = get_current_configured_block_costs(data)
    list_of_instruments = configured.index

    list_of_broker = get_broker_block_costs(list_of_instruments)

    return pd.concat([configured, list_of_broker], axis=1)

def get_current_configured_block_costs(data) -> pd.Series:
    diag_instruments = diagInstruments(data)

    return diag_instruments.get_block_commissions_as_series()

def get_broker_block_costs(list_of_instruments_codes: List[str]) ->pd.Series:
    db = dataBroker()
    dc = dataContracts()

    list_of_priced_contracts = [futuresContract(instrument_code, dc.get_priced_contract_id(instrument_code)) for instrument_code in list_of_instruments_codes]

    return pd.Series(
        [db.get_commission_for_contract(contract) for contract in list_of_priced_contracts],
        index = list_of_instruments_codes
    )