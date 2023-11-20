from syscore.constants import arg_not_supplied
from sysobjects.roll_calendars import rollCalendar
from sysdata.csv.csv_roll_calendars import csvRollCalendarData
from sysdata.csv.csv_roll_parameters import csvRollParametersData

from sysproduction.data.prices import diagPrices


"""
Generate the roll calendars from existing data
"""

if __name__ == "__main__":
    input("Will overwrite existing data are you sure?! CTL-C to abort")

    diag_prices = diagPrices()

    output_datapath = arg_not_supplied
    csv_roll_calendars = csvRollCalendarData(arg_not_supplied)
    csv_rollparameters = csvRollParametersData()
    db_multiple_prices = diag_prices.db_futures_multiple_prices_data

    instrument_list = db_multiple_prices.get_list_of_instruments()

    for instrument_code in instrument_list:
        print(instrument_code)
        multiple_prices = db_multiple_prices.get_multiple_prices(instrument_code)

        roll_parameters = csv_rollparameters.get_roll_parameters(instrument_code)
        roll_calendar = rollCalendar.back_out_from_multiple_prices(multiple_prices)
        print("Calendar:")
        print(roll_calendar)

        # We ignore duplicates since this is run regularly
        csv_roll_calendars.add_roll_calendar(
            instrument_code, roll_calendar, ignore_duplication=True
        )
