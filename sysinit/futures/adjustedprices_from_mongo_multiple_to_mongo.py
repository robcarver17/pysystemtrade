"""
We create adjusted prices using multiple prices stored in arctic

We then store those adjusted prices in arctic

"""

from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData

from sysdata.futures.adjusted_prices import futuresAdjustedPrices


if __name__ == '__main__':
    arctic_multiple_prices = arcticFuturesMultiplePricesData()
    artic_adjusted_prices = arcticFuturesAdjustedPricesData()

    instrument_list = arctic_multiple_prices.get_list_of_instruments()

    for instrument_code in instrument_list:
        print(instrument_code)

        multiple_prices = arctic_multiple_prices.get_multiple_prices(instrument_code)
        adjusted_prices = futuresAdjustedPrices.stich_multiple_prices(multiple_prices)

        print(adjusted_prices)

        artic_adjusted_prices.add_adjusted_prices(instrument_code, adjusted_prices)
