"""
We create multiple prices using:

- roll calendars, stored in csv
- individual futures contract prices, stored in arctic

We then store those multiple prices in: (depending on options)

- arctic
- .csv
"""

from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysdata.csv.csv_roll_calendars import csvRollCalendarData
from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData

from sysdata.futures.multiple_prices import futuresMultiplePrices

# could get these from stdin
ADD_TO_ARCTIC = True
ADD_TO_CSV = True

if __name__ == '__main__':
    csv_roll_calendars = csvRollCalendarData()
    artic_individual_futures_prices = arcticFuturesContractPriceData()
    arctic_multiple_prices = arcticFuturesMultiplePricesData()
    csv_multiple_prices = csvFuturesMultiplePricesData()

    instrument_list = artic_individual_futures_prices.get_instruments_with_price_data()

    for instrument_code in instrument_list:
        print(instrument_code)
        roll_calendar = csv_roll_calendars.get_roll_calendar(instrument_code)
        dict_of_futures_contract_prices = artic_individual_futures_prices.get_all_prices_for_instrument(instrument_code)
        dict_of_futures_contract_settlement_prices = dict_of_futures_contract_prices.settlement_prices()

        multiple_prices = futuresMultiplePrices.create_from_raw_data(roll_calendar, dict_of_futures_contract_settlement_prices)

        print(multiple_prices)

        if ADD_TO_ARCTIC:
            arctic_multiple_prices.add_multiple_prices(instrument_code, multiple_prices, ignore_duplication=True)
        if ADD_TO_CSV:
            csv_multiple_prices.add_multiple_prices(instrument_code, multiple_prices, ignore_duplication=True)

