"""
Copy from csv repo files to arctic for multiple prices
"""

from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData

if __name__ == "__main__":
    arctic_multiple_prices = arcticFuturesMultiplePricesData()
    csv_multiple_prices = csvFuturesMultiplePricesData()

    instrument_list = csv_multiple_prices.get_list_of_instruments()

    for instrument_code in instrument_list:
        print(instrument_code)
        multiple_prices = csv_multiple_prices.get_multiple_prices(
            instrument_code)

        print(multiple_prices)

        arctic_multiple_prices.add_multiple_prices(
            instrument_code, multiple_prices, ignore_duplication=True
        )
