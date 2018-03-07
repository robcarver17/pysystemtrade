"""
Create a list of futures contracts, then write to mongodb database

NOTE: MAY NOT BE REQUIRED
"""

from sysdata.futures.contracts import listOfFuturesContracts
from sysdata.mongodb.mongo_futures_contracts import mongoFuturesContractData
import datetime

## Need to get this configuration data from somewhere
instrument_code = "EDOLLAR"
first_date = datetime.datetime(2000,1,1)
last_date = datetime.datetime(2002,1,1)
rollcycle_string = "HMUZ"

#quandl.ApiConfig.api_key = 'your key here'
list_of_contracts = listOfFuturesContracts.series_of_contracts_within_daterange(instrument_code, first_date,
                                                                                last_date, rollcycle_string)

data = mongoFuturesContractData()
[data.add_contract_data(contract_object) for contract_object in list_of_contracts]
