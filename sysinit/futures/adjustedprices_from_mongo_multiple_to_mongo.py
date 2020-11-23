"""
We create adjusted prices using multiple prices stored in arctic

We then store those adjusted prices in arctic and/or csv

"""

from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData

from sysobjects.adjusted_prices import futuresAdjustedPrices


def _get_data_inputs(csv_adj_data_path):
    arctic_multiple_prices = arcticFuturesMultiplePricesData()
    arctic_adjusted_prices = arcticFuturesAdjustedPricesData()
    csv_adjusted_prices = csvFuturesAdjustedPricesData(csv_adj_data_path)

    return arctic_multiple_prices, arctic_adjusted_prices, csv_adjusted_prices


def process_adjusted_prices_all_instruments(
    csv_adj_data_path=None, ADD_TO_ARCTIC=True, ADD_TO_CSV=False
):
    arctic_multiple_prices, _notused, _alsonotused = _get_data_inputs(
        csv_adj_data_path)
    instrument_list = arctic_multiple_prices.get_list_of_instruments()
    for instrument_code in instrument_list:
        print(instrument_code)
        process_adjusted_prices_single_instrument(
            instrument_code,
            csv_adj_data_path=csv_adj_data_path,
            ADD_TO_ARCTIC=ADD_TO_ARCTIC,
            ADD_TO_CSV=ADD_TO_CSV,
        )


def process_adjusted_prices_single_instrument(
        instrument_code,
        csv_adj_data_path=None,
        ADD_TO_ARCTIC=True,
        ADD_TO_CSV=False):
    (
        arctic_multiple_prices,
        arctic_adjusted_prices,
        csv_adjusted_prices,
    ) = _get_data_inputs(csv_adj_data_path)
    multiple_prices = arctic_multiple_prices.get_multiple_prices(
        instrument_code)
    adjusted_prices = futuresAdjustedPrices.stich_multiple_prices(
        multiple_prices, forward_fill=True
    )

    print(adjusted_prices)

    if ADD_TO_ARCTIC:
        arctic_adjusted_prices.add_adjusted_prices(
            instrument_code, adjusted_prices, ignore_duplication=True
        )
    if ADD_TO_CSV:
        csv_adjusted_prices.add_adjusted_prices(
            instrument_code, adjusted_prices, ignore_duplication=True
        )

    return adjusted_prices
