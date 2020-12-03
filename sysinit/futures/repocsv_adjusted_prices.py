"""
Copy from csv repo files to arctic for adjusted prices
"""
from syscore.objects import arg_not_supplied
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData

if __name__ == "__main__":
    input("Will overwrite existing prices are you sure?! CTL-C to abort")
    artic_adjusted_prices = arcticFuturesAdjustedPricesData()

    ## MODIFY PATH TO USE SOMETHING OTHER THAN DEFAULT
    csv_adj_datapath = arg_not_supplied
    csv_adjusted_prices = csvFuturesAdjustedPricesData(csv_adj_datapath)

    instrument_list = csv_adjusted_prices.get_list_of_instruments()

    for instrument_code in instrument_list:
        print(instrument_code)

        adjusted_prices = csv_adjusted_prices.get_adjusted_prices(
            instrument_code)

        print(adjusted_prices)

        artic_adjusted_prices.add_adjusted_prices(
            instrument_code, adjusted_prices, ignore_duplication=True
        )
