from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData
from sysdata.futures.roll_calendars import rollCalendar
from sysdata.csv.csv_roll_calendars import csvRollCalendarData

import sys

"""
Generate a 'best guess' roll calendar based on some price data for individual contracts

"""

output_datapath = "/home/rob/data/csv_temp/roll_calendars"

if __name__ == '__main__':

    #instrument_code = sys.argv[1]
    instrument_code="BOBL"

    ##
    artic_prices = arcticFuturesContractPriceData()
    mongo_rollparameters = mongoRollParametersData()
    csv_roll_calendars = csvRollCalendarData(output_datapath)

    dict_of_all_futures_contract_prices = artic_prices.get_all_prices_for_instrument(instrument_code)
    dict_of_futures_contract_prices = dict_of_all_futures_contract_prices.final_prices()

    roll_parameters = mongo_rollparameters.get_roll_parameters(instrument_code)

    ## might take a few seconds
    print("Prepping roll calendar... might take a few seconds")
    roll_calendar = rollCalendar.create_from_prices(dict_of_futures_contract_prices, roll_parameters)

    ## checks - this might fail
    check_monotonic = roll_calendar.check_if_date_index_monotonic()

    ## this should never fail
    check_valid = roll_calendar.check_dates_are_valid_for_prices(dict_of_futures_contract_prices)

    # Write to csv
    # Will not work if an existing calendar exists

    check_happy_to_write = input("Are you ok to write this csv? [might be worth writing and hacking manually] (yes/other)?")
    if check_happy_to_write == "yes":
        csv_roll_calendars.add_roll_calendar(roll_calendar, instrument_code)
    else:
        print("Not writing")