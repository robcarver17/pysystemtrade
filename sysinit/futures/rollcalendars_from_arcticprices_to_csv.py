from syscore.interactive.input import true_if_answer_is_yes
from syscore.constants import arg_not_supplied

from sysobjects.rolls import rollParameters
from sysobjects.roll_calendars import rollCalendar
from sysdata.csv.csv_roll_calendars import csvRollCalendarData
from sysdata.csv.csv_roll_parameters import csvRollParametersData
from sysdata.futures.rolls_parameters import rollParametersData
from sysproduction.data.prices import get_valid_instrument_code_from_user, diagPrices
from sysproduction.data.production_data_objects import (
    get_class_for_data_type,
    FUTURES_CONTRACT_PRICE_DATA,
)

from sysdata.data_blob import dataBlob

diag_prices = diagPrices()

parquet_futures_contract_price_data = diag_prices.db_futures_contract_price_data

"""
Generate a 'best guess' roll calendar based on some price data for individual contracts

"""


def build_and_write_roll_calendar(
    instrument_code,
    output_datapath=arg_not_supplied,
    write=True,
    check_before_writing=True,
    input_prices=arg_not_supplied,
    roll_parameters_data: rollParametersData = arg_not_supplied,
    roll_parameters: rollParameters = arg_not_supplied,
):
    if output_datapath is arg_not_supplied:
        print(
            "*** WARNING *** This will overwrite the provided roll calendar. Might be better to use a temporary directory!"
        )
    else:
        print("Writing to %s" % output_datapath)

    if input_prices is arg_not_supplied:
        prices = parquet_futures_contract_price_data
    else:
        prices = input_prices

    if roll_parameters is arg_not_supplied:
        if roll_parameters_data is arg_not_supplied:
            roll_parameters_data = csvRollParametersData()
        roll_parameters = roll_parameters_data.get_roll_parameters(instrument_code)

    csv_roll_calendars = csvRollCalendarData(output_datapath)

    dict_of_all_futures_contract_prices = prices.get_merged_prices_for_instrument(
        instrument_code
    )
    dict_of_futures_contract_prices = dict_of_all_futures_contract_prices.final_prices()

    # might take a few seconds
    print("Prepping roll calendar... might take a few seconds")
    roll_calendar = rollCalendar.create_from_prices(
        dict_of_futures_contract_prices, roll_parameters
    )

    # checks - this might fail
    roll_calendar.check_if_date_index_monotonic()

    # this should never fail
    roll_calendar.check_dates_are_valid_for_prices(dict_of_futures_contract_prices)

    # Write to csv
    # Will not work if an existing calendar exists
    if write:
        if check_before_writing:
            check_happy_to_write = true_if_answer_is_yes(
                "Are you ok to write this csv to path %s/%s.csv? [might be worth writing and hacking manually]?"
                % (csv_roll_calendars.datapath, instrument_code)
            )
        else:
            check_happy_to_write = True

        if check_happy_to_write:
            print("Adding roll calendar")
            csv_roll_calendars.add_roll_calendar(
                instrument_code, roll_calendar, ignore_duplication=True
            )
        else:
            print("Not writing - not happy")

    return roll_calendar


def check_saved_roll_calendar(
    instrument_code, input_datapath=arg_not_supplied, input_prices=arg_not_supplied
):
    if input_datapath is None:
        print(
            "This will check the roll calendar in the default directory : are you are that's what you want to do?"
        )

    csv_roll_calendars = csvRollCalendarData(input_datapath)

    roll_calendar = csv_roll_calendars.get_roll_calendar(instrument_code)

    if input_prices is arg_not_supplied:
        prices = parquet_futures_contract_price_data
    else:
        prices = input_prices

    dict_of_all_futures_contract_prices = prices.get_merged_prices_for_instrument(
        instrument_code
    )
    dict_of_futures_contract_prices = dict_of_all_futures_contract_prices.final_prices()

    print(roll_calendar)

    # checks - this might fail
    roll_calendar.check_if_date_index_monotonic()

    # this should never fail
    roll_calendar.check_dates_are_valid_for_prices(dict_of_futures_contract_prices)

    return roll_calendar


if __name__ == "__main__":
    input("Will overwrite existing roll calendar are you sure?! CTL-C to abort")
    instrument_code = get_valid_instrument_code_from_user(source="single")
    ## MODIFY DATAPATH IF REQUIRED
    # build_and_write_roll_calendar(instrument_code, output_datapath=arg_not_supplied)
    build_and_write_roll_calendar(instrument_code, output_datapath="/home/rob/")
