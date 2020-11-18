
from sysobjects.roll_calendars import rollCalendar
from syslogdiag.log import logtoscreen

USE_CHILD_CLASS_ROLL_CALENDAR_ERROR = (
    "You need to use a child class of rollCalendarData"
)


class rollCalendarData(object):
    """
    Class to read / write roll calendars

    We wouldn't normally use this base class, but inherit from it for a specific data source eg Arctic
    """

    def __init__(self, log=logtoscreen):
        self._log = log

    @property
    def log(self):
        return self._log

    def __repr__(self):
        return "rollCalendarData base class - DO NOT USE"

    def keys(self):
        return self.get_list_of_instruments()

    def __getitem__(self, instrument_code):
        return self.get_roll_calendar(instrument_code)

    def get_list_of_instruments(self):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def get_roll_calendar(self, instrument_code):
        if self.is_code_in_data(instrument_code):
            return self._get_roll_calendar_without_checking(instrument_code)
        else:
            return rollCalendar.create_empty()

    def _get_roll_calendar_without_checking(self, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def delete_roll_calendar(self, instrument_code, are_you_sure=False):
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

    def _delete_roll_calendar_data_without_any_warning_be_careful(self,
            instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def is_code_in_data(self, instrument_code):
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_roll_calendar(
        self, roll_calendar, instrument_code, ignore_duplication=False
    ):

        self.log.label(instrument_code=instrument_code)

        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                raise self.log.warn(
                    "There is already %s in the data, you have to delete it first" %
                    instrument_code)

        self._add_roll_calendar_without_checking_for_existing_entry(
            roll_calendar, instrument_code
        )

        self.log.terse(
            "Added roll calendar for instrument %s" %
            instrument_code)

    def _add_roll_calendar_without_checking_for_existing_entry(
        self, roll_calendar, instrument_code
    ):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)
