from sysdata.csv.csv_sim_futures_data import csvFuturesSimData
from sysdata.futures.roll_calendars import rollCalendar
from sysdata.csv.csv_roll_calendars import csvRollCalendarData
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData

"""
Generate the roll calendars from existing data
"""

if __name__ == '__main__':
    csv_roll_calendars = csvRollCalendarData()
    sim_futures_data = csvFuturesSimData()
    mongo_rollparameters = mongoRollParametersData()

    instrument_list = sim_futures_data.get_instrument_list()

    for instrument_code in instrument_list:
        print(instrument_code)
        current_and_forward_data = sim_futures_data.get_current_and_forward_price_data(instrument_code)

        roll_parameters = mongo_rollparameters.get_roll_parameters(instrument_code)
        roll_calendar = rollCalendar.back_out_from_current_and_forward_data(current_and_forward_data, roll_parameters)
        print("Calendar:")
        print(roll_calendar)

        ## We ignore duplicates since this is run regularly
        csv_roll_calendars.add_roll_calendar(roll_calendar, instrument_code, ignore_duplication=True)
