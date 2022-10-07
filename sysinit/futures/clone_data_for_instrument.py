from sysdata.arctic.arctic_futures_per_contract_prices import (
    arcticFuturesContractPriceData,
)
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData

from sysdata.csv.csv_roll_calendars import csvRollCalendarData
from sysdata.csv.csv_multiple_prices import csvFuturesMultiplePricesData
from sysdata.csv.csv_adjusted_prices import csvFuturesAdjustedPricesData

from sysobjects.contracts import futuresContract
from syscore.dateutils import DAILY_PRICE_FREQ, HOURLY_FREQ
from sysobjects.multiple_prices import futuresMultiplePrices
from sysobjects.adjusted_prices import futuresAdjustedPrices


db_data_individual_prices = arcticFuturesContractPriceData()
db_data_multiple_prices = arcticFuturesMultiplePricesData()
db_data_adjusted_prices = arcticFuturesAdjustedPricesData()

csv_roll_calendar = csvRollCalendarData()
csv_multiple = csvFuturesMultiplePricesData()
csv_adjusted = csvFuturesAdjustedPricesData()


def clone_data_for_instrument(
    instrument_from: str, instrument_to: str, write_to_csv: bool = False,
        inverse: bool = False
):

    clone_prices_per_contract(instrument_from, instrument_to, inverse=inverse)
    if write_to_csv:
        clone_roll_calendar(instrument_from, instrument_to)

    clone_multiple_prices(instrument_from, instrument_to, write_to_csv=write_to_csv, inverse=inverse)
    clone_adjusted_prices(instrument_from, instrument_to, write_to_csv=write_to_csv, inverse=inverse)


def clone_prices_per_contract(instrument_from: str, instrument_to: str,
                              list_of_contract_dates = None,
                              ignore_duplication = False,
                              inverse: bool = False,
                              multiplier: float = 1.0):

    if list_of_contract_dates is None:
        list_of_contract_dates = (
            db_data_individual_prices.contract_dates_with_merged_price_data_for_instrument_code(
                instrument_from
            )
        )

    _ = [
        clone_single_contract(instrument_from, instrument_to, contract_date,
                              ignore_duplication = ignore_duplication,
                              inverse=inverse, multiplier = multiplier)
        for contract_date in list_of_contract_dates
    ]

def clone_single_contract(instrument_from: str, instrument_to: str,
                          contract_date: str, ignore_duplication = False,
                          inverse: bool = False,
                          multiplier: float = 1.0):

    futures_contract_from = futuresContract(instrument_from, contract_date)
    futures_contract_to = futuresContract(instrument_to, contract_date)

    data_in = db_data_individual_prices.get_merged_prices_for_contract_object(
        futures_contract_from
    )

    if inverse:
        data_in = data_in.inverse()

    data_in = data_in.multiply_prices(multiplier)

    db_data_individual_prices.write_merged_prices_for_contract_object(
        futures_contract_to, futures_price_data=data_in,
        ignore_duplication=ignore_duplication
    )

    hourly_data_in = db_data_individual_prices.get_prices_at_frequency_for_contract_object(
        futures_contract_from, frequency=HOURLY_FREQ
    )
    if len(hourly_data_in)>0:
        if inverse:
            hourly_data_in = hourly_data_in.inverse()

        hourly_data_in = hourly_data_in.multiply_prices(multiplier)

        db_data_individual_prices.write_prices_at_frequency_for_contract_object(
            futures_contract_to,
            futures_price_data=hourly_data_in,
            frequency=HOURLY_FREQ
        )

    daily_data_in = db_data_individual_prices.get_prices_at_frequency_for_contract_object(
        futures_contract_from, frequency=DAILY_PRICE_FREQ
    )
    if len(daily_data_in)>0:
        if inverse:
            daily_data_in = daily_data_in.inverse()

        daily_data_in = daily_data_in.multiply_prices(multiplier)

        db_data_individual_prices.write_prices_at_frequency_for_contract_object(
            futures_contract_to,
            futures_price_data=daily_data_in,
            frequency=DAILY_PRICE_FREQ
        )



def clone_roll_calendar(instrument_from: str, instrument_to: str):

    roll_calendar = csv_roll_calendar.get_roll_calendar(instrument_from)
    csv_roll_calendar.add_roll_calendar(instrument_to, roll_calendar=roll_calendar)


def clone_multiple_prices(
    instrument_from: str, instrument_to: str, write_to_csv: bool = True, ignore_duplication = False,
inverse: bool = False
):

    prices = db_data_multiple_prices.get_multiple_prices(instrument_from)
    if inverse:
        prices = prices.inverse()

    db_data_multiple_prices.add_multiple_prices(
        instrument_to, multiple_price_data=prices, ignore_duplication=ignore_duplication
    )

    if write_to_csv:
        csv_multiple.add_multiple_prices(instrument_to, multiple_price_data=prices)


def clone_adjusted_prices(
    instrument_from: str, instrument_to: str, write_to_csv: bool = True,
        ignore_duplication = False, inverse: bool = False
):

    prices = db_data_adjusted_prices.get_adjusted_prices(instrument_from)
    if inverse:
        prices = futuresAdjustedPrices(1/prices)

    db_data_adjusted_prices.add_adjusted_prices(
        instrument_to, adjusted_price_data=prices,
        ignore_duplication=ignore_duplication
    )
    if write_to_csv:
        csv_adjusted.add_adjusted_prices(instrument_to, adjusted_price_data=prices)
