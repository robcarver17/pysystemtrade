from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData


def init_arctic_with_csv_futures_contract_prices(datapath):
    csv_multiple_prices = csvFuturesMultiplePricesData()
    csv_adj_prices = csvFuturesAdjustedPricesData()
    input("WARNING THIS WILL ERASE ANY EXISTING ARCTIC PRICES WITH DATA FROM %s,%s ARE YOU SURE?!" % (csv_adj_prices.datapath, csv_multiple_prices.datapath))

    instrument_codes = csv_multiple_prices.get_list_of_instruments()
    for instrument_code in instrument_codes:
        init_arctic_with_csv_prices_for_code(instrument_code)

def init_arctic_with_csv_prices_for_code(instrument_code:str):
    print(instrument_code)
    csv_mult = csvFuturesMultiplePricesData()
    a_mult = arcticFuturesMultiplePricesData()

    mult = csv_mult.get_multiple_prices(instrument_code)
    a_mult.add_multiple_prices(instrument_code, mult, ignore_duplication=True)

    csv_adj = csvFuturesAdjustedPricesData()
    a_adj = arcticFuturesAdjustedPricesData()

    adj = csv_adj.get_adjusted_prices(instrument_code)
    a_adj.add_adjusted_prices(instrument_code, adj, ignore_duplication=True)