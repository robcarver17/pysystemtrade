from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysobjects.roll_calendars import rollCalendar
from sysdata.csv.csv_roll_calendars import csvRollCalendarData

"""
Generate the roll calendars from existing data
"""

def generate_roll_calendars_from_provided_multiple_csv_prices(output_datapath):
    input("This will overwrite the roll calendars in %s : CRTL-C if you aren't sure!" % output_datapath)
    csv_roll_calendars = csvRollCalendarData(datapath=output_datapath)
    sim_futures_data = csvFuturesSimData()

    instrument_list = sim_futures_data.get_instrument_list()

    for instrument_code in instrument_list:
        print(instrument_code)
        multiple_prices = sim_futures_data.get_multiple_prices(
            instrument_code)

        roll_calendar = rollCalendar.back_out_from_multiple_prices(
            multiple_prices
        )
        print("Calendar:")
        print(roll_calendar)

        # We ignore duplicates since this is run regularly
        csv_roll_calendars.add_roll_calendar(instrument_code, roll_calendar, ignore_duplication=True)

if __name__ == "__main__":
    datapath ="MUST SUPPLY A DATAPATH"
    generate_roll_calendars_from_provided_multiple_csv_prices(datapath)