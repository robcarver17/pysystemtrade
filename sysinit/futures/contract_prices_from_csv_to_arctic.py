from sysdata.csv.csv_futures_contract_prices import csvFuturesContractPriceData
from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysobjects.contracts import futuresContract

DEFAULT_PATH = "/home/rob/data/backup/contract_prices/"

def init_arctic_with_csv_futures_contract_prices(datapath):
    csv_prices = csvFuturesContractPriceData(datapath)
    input("WARNING THIS WILL ERASE ANY EXISTING ARCTIC PRICES WITH DATA FROM %s ARE YOU SURE?!" % csv_prices.datapath)

    instrument_codes = csv_prices.get_list_of_instrument_codes_with_price_data()
    for instrument_code in instrument_codes:
        init_arctic_with_csv_futures_contract_prices_for_code(instrument_code, datapath)

def init_arctic_with_csv_futures_contract_prices_for_code(instrument_code:str, datapath: str = DEFAULT_PATH):
    print(instrument_code)
    csv_prices = csvFuturesContractPriceData(datapath)
    arctic_prices = arcticFuturesContractPriceData()
    csv_price_dict = csv_prices.get_all_prices_for_instrument(instrument_code)
    for contract_date_str, prices_for_contract in csv_price_dict.items():
        contract = futuresContract(instrument_code, contract_date_str)
        arctic_prices.write_prices_for_contract_object(contract, prices_for_contract, ignore_duplication=True)