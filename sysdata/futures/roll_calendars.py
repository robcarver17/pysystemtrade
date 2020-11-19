from sysdata.base_data import baseData
from sysobjects.roll_calendars import rollCalendar
from syslogdiag.log import logtoscreen

USE_CHILD_CLASS_ROLL_CALENDAR_ERROR = (
    "You need to use a child class of rollCalendarData"
)


class rollCalendarData(baseData):
    """
    Class to read / write roll calendars

    We wouldn't normally use this base class, but inherit from it for a specific data source eg Arctic
    """

    def __init__(self, log=logtoscreen):
        super().__init__(log=log)


    def __repr__(self):
        return "rollCalendarData base class - DO NOT USE"

    def keys(self) ->str:
        return self.get_list_of_instruments()

    def __getitem__(self, instrument_code:str) -> rollCalendar:
        return self.get_roll_calendar(instrument_code)


    def get_roll_calendar(self, instrument_code:str) -> rollCalendar:
        if self.is_code_in_data(instrument_code):
            return self._get_roll_calendar_without_checking(instrument_code)
        else:
            return rollCalendar.create_empty()

    def delete_roll_calendar(self, instrument_code:str, are_you_sure=False):
        self.log.label(instrument_code=instrument_code)

        if are_you_sure:
            if self.is_code_in_data(instrument_code):
                self._delete_roll_calendar_data_without_any_warning_be_careful(
                    instrument_code
                )
                self.log.terse(
                    "Deleted roll calendar for %s" %
                    instrument_code)

            else:
                # doesn't exist anyway
                self.log.warn(
                    "Tried to delete roll calendar for non existent instrument code %s" %
                    instrument_code)
        else:
            self.log.error(
                "You need to call delete_roll_calendar with a flag to be sure"
            )


    def add_roll_calendar(self, instrument_code: str, roll_calendar: rollCalendar, ignore_duplication: bool = False):

        self.log.label(instrument_code=instrument_code)

        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                raise self.log.warn(
                    "There is already %s in the data, you have to delete it first" %
                    instrument_code)

        self._add_roll_calendar_without_checking_for_existing_entry(instrument_code, roll_calendar)

        self.log.terse(
            "Added roll calendar for instrument %s" %
            instrument_code)

    def is_code_in_data(self, instrument_code:str) -> bool:
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def get_list_of_instruments(self) -> list:
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def _get_roll_calendar_without_checking(self, instrument_code) -> rollCalendar:
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)


    def _delete_roll_calendar_data_without_any_warning_be_careful(self,
            instrument_code:str):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)


    def _add_roll_calendar_without_checking_for_existing_entry(self, instrument_code:str, roll_calendar: rollCalendar):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)
