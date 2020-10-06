"""
We create multiple prices using:

- roll calendars, stored in csv
- individual futures contract prices, stored in arctic

We then store those multiple prices in: (depending on options)

- arctic
- .csv
"""

from sysdata.arctic.arctic_futures_per_contract_prices import (
    arcticFuturesContractPriceData,
)
from sysdata.csv.csv_roll_calendars import csvRollCalendarData
from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData

from sysdata.futures.multiple_prices import futuresMultiplePrices


def _get_data_inputs(csv_roll_data_path, csv_multiple_data_path):
    csv_roll_calendars = csvRollCalendarData(csv_roll_data_path)
    arctic_individual_futures_prices = arcticFuturesContractPriceData()
    arctic_multiple_prices = arcticFuturesMultiplePricesData()
    csv_multiple_prices = csvFuturesMultiplePricesData(csv_multiple_data_path)

    return (
        csv_roll_calendars,
        arctic_individual_futures_prices,
        arctic_multiple_prices,
        csv_multiple_prices,
    )


def process_multiple_prices_all_instruments(
    csv_multiple_data_path=None,
    csv_roll_data_path=None,
    ADD_TO_ARCTIC=True,
    ADD_TO_CSV=False,
):

    (
        _not_used1,
        arctic_individual_futures_prices,
        _not_used2,
        _not_used3,
    ) = _get_data_inputs(csv_roll_data_path, csv_multiple_data_path)
    instrument_list = arctic_individual_futures_prices.get_instruments_with_price_data()

    for instrument_code in instrument_list:
        print(instrument_code)
        process_multiple_prices_single_instrument(
            instrument_code,
            csv_multiple_data_path=csv_multiple_data_path,
            csv_roll_data_path=csv_roll_data_path,
            ADD_TO_ARCTIC=ADD_TO_ARCTIC,
            ADD_TO_CSV=ADD_TO_CSV,
        )


def process_multiple_prices_single_instrument(
    instrument_code,
    csv_multiple_data_path=None,
    csv_roll_data_path=None,
    ADD_TO_ARCTIC=True,
    ADD_TO_CSV=False,
):

    (
        csv_roll_calendars,
        arctic_individual_futures_prices,
        arctic_multiple_prices,
        csv_multiple_prices,
    ) = _get_data_inputs(csv_roll_data_path, csv_multiple_data_path)

    roll_calendar = csv_roll_calendars.get_roll_calendar(instrument_code)
    dict_of_futures_contract_prices = (
        arctic_individual_futures_prices.get_all_prices_for_instrument(instrument_code))
    dict_of_futures_contract_closing_prices = (
        dict_of_futures_contract_prices.final_prices()
    )

    multiple_prices = futuresMultiplePrices.create_from_raw_data(
        roll_calendar, dict_of_futures_contract_closing_prices
    )

    print(multiple_prices)

    if ADD_TO_ARCTIC:
        arctic_multiple_prices.add_multiple_prices(
            instrument_code, multiple_prices, ignore_duplication=True
        )
    if ADD_TO_CSV:
        csv_multiple_prices.add_multiple_prices(
            instrument_code, multiple_prices, ignore_duplication=True
        )

    return multiple_prices
