"""
Here is an example of how we get individual futures price data from quandl
"""

from sysdata.futuresdata import listOfFuturesContracts
from sysdata.quandl.futures import quandl_get_futures_contract_historic_data, listOfQuandlFuturesContracts

import quandl
import datetime

instrument_code = "EDOLLAR"
first_date = datetime.datetime(2000,1,1)
last_date = datetime.datetime(2002,1,1)
rollcycle_string = "HMUZ"

#quandl.ApiConfig.api_key = 'your key here'
list_of_contracts = listOfFuturesContracts.series_of_contracts_within_daterange(instrument_code, first_date,
                                                                                last_date, rollcycle_string)

list_of_quandl_contracts = listOfQuandlFuturesContracts(list_of_contracts)

q_data = dict([(contract.ident(), quandl_get_futures_contract_historic_data(contract)) for contract in list_of_quandl_contracts])
