from sysdata.csv.csv_futures_contract_prices import csvFuturesContractPriceData
from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysobjects.contracts import futuresContract


def init_arctic_with_csv_futures_contract_prices(datapath: str):
    csv_prices = csvFuturesContractPriceData(datapath)
    input("WARNING THIS WILL ERASE ANY EXISTING ARCTIC PRICES WITH DATA FROM %s ARE YOU SURE?! (CTRL-C TO STOP)" % csv_prices.datapath)

    instrument_codes = csv_prices.get_list_of_instrument_codes_with_price_data()
    instrument_codes.sort()
    for instrument_code in instrument_codes:
        init_arctic_with_csv_futures_contract_prices_for_code(instrument_code, datapath)

def init_arctic_with_csv_futures_contract_prices_for_code(instrument_code:str, datapath: str):
    print(instrument_code)
    csv_prices = csvFuturesContractPriceData(datapath)
    arctic_prices = arcticFuturesContractPriceData()

    print("Getting .csv prices may take some time")
    csv_price_dict = csv_prices.get_all_prices_for_instrument(instrument_code)

    for contract_date_str, prices_for_contract in csv_price_dict.items():
        print(contract_date_str)
        contract = futuresContract(instrument_code, contract_date_str)
        arctic_prices.write_prices_for_contract_object(contract, prices_for_contract, ignore_duplication=True)