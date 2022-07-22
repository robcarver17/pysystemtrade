"""
Copy from csv repo files to arctic for multiple prices
"""

from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData

if __name__ == "__main__":
    input("Will overwrite existing prices are you sure?! CTL-C to abort")

    arctic_multiple_prices = arcticFuturesMultiplePricesData()
    csv_multiple_prices = csvFuturesMultiplePricesData()

    instrument_code = input("Instrument code? <return for ALL instruments> ")
    if instrument_code == "":
        instrument_list = csv_multiple_prices.get_list_of_instruments()
    else:
        instrument_list = [instrument_code]

    for instrument_code in instrument_list:
        print(instrument_code)
        multiple_prices = csv_multiple_prices.get_multiple_prices(instrument_code)

        print(multiple_prices)

        arctic_multiple_prices.add_multiple_prices(
            instrument_code, multiple_prices, ignore_duplication=True
        )
