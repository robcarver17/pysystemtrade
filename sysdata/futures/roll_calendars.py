from sysdata.data import baseData
from sysdata.futures.contracts import listOfFuturesContracts
from sysdata.futures.instruments import futuresInstrument
import pandas as pd

class _single_roll_row(object):
    def __init__(self, reference_date, current_contract, next_contract):
        """
        SHOULD THIS NORMALLY BE GENERATED USING ROLL PARAMETERS AND THE REFERENCE DATE?

        :param reference_date: relevant date
        :param current_contract: futuresContract
        :param next_contract:  futuresContract
        """

        self.reference_date = reference_date
        self.current_contract = current_contract
        self.next_contract = next_contract


    def to_pd_row(self):
        pass



class rollCalendar(pd.dataframe):
    """
    A roll calendar is a dataframe telling us when we have rolled futures contracts in the past (or would have in a backtest)

    It has a datetime index, and two columns; current_contract and next_contract

    There are two types of calendar: padded (where we have all the business days in between rolls with entries)
       and sparse (where only the days when things change are shown)

    Normally a roll calendar would be created using the following process:
     - start with a list of futures contracts and some rollParameters
     - using a rollParameters object we work out roughly what the rolls should be (in an ideal world with available prices all the time)
     - then using a list of futures contract price data we shift the rolls around so that rolls are possible on a given date

    Another way of getting a roll calendar is to back it out from an existing 'carry data' (eg as we have in legacy csv)

    Sometimes you need to manually hack roll calendars, so it's also useful to have a csv convenience method for read/write
    (we don't have a 'full' csv data object to discourage storing them in this format)

    When combined with a list of futures contract price data a roll calendar can be used to create a back adjusted price series
    This can then be stored.
    (We don't create these 'on line' as it's a bit slow. We can add additional rows to a back adjusted price series just
        from the current price. Then the re-adjustment can happen again on each roll. Could use Arctic vintage method here?)
    """

    def generate_approximate_calendar(roll_parameters_object, list_of_contracts):
        """
        Using a rollData object we work out roughly what the rolls should be (in an ideal world with available prices all the time)
          for contracts held between start_date and end_date

        Called by __init__

        :param roll_parameters_object: rollData
        :param start_date: datetime.datetime
        :param end_date: datetime.datetime
        :return: rollCalendar
        """

        theoretical_roll_dates=[futures_contract.contract_date.want_to_roll() for futures_contract in list_of_contracts]

        # On the roll date we stop holding the relevant contract, and end up holding the next one
        contracts_to_hold_on_each_roll = list_of_contracts[1:]

        # so we need to drop the last entry, to keep things lined up
        theoretical_roll_dates = theoretical_roll_dates[:-1]

        # We also need a list of the next contract along


        # make sure it is sparse

        return rollCalendar

    @classmethod
    def back_out_from_carry_data(rollCalendar, carry_data):
        """

        :param carry_data: output from futuresDataForSim.FuturesData.get_instrument_raw_carry_data(instrument_code)
        :return: rollCalendar
        """

        # make sure it is sparse

        rollCalendar.make_sparse()

        return rollCalendar

    @classmethod
    def read_csv(rollCalendar, file_name_with_dots):
        """

        :param file_name_with_dots: .csv file containing  rollCalendar
        :return: rollCalendar
        """

        # make sure it is sparse

        rollCalendar.make_sparse()

        return rollCalendar

    def adjust_to_price_series(self, list_of_futures_per_contract_prices):
        """
        Adjust an approximate roll calendar so that we have matching dates on each expiry

        Called by __init__

        :param list_of_futures_per_contract_prices: dictFuturesContractPrices
        :return: Nothing, modifies self
        """

        pass

    def write_csv(self, file_name_with_dots):
        """
        Writes roll calendar to file

        :param list_of_futures_per_contract_prices: dictFuturesContractPrices
        :return: Nothing
        """
        # make sure it is sparse

        rollCalendar.make_sparse()

    def as_sparse(self):
        """
        Remove all extraenous entries so only have roll dates

        :return: sparse rollCalendar
        """

        pass

    def as_padded(self):
        """
        Add additional entries so have lines for every business day

        :return: padded rollCalendar
        """

        pass

USE_CHILD_CLASS_ROLL_CALENDAR_ERROR = "You need to use a child class of rollCalendarData"


class rollCalendarData(baseData):
    """
    Class to read / write roll calendars

    We wouldn't normally use this base class, but inherit from it for a specific data source eg Arctic
    """

    def __repr__(self):
        return "rollCalendarData base class - DO NOT USE"

    def keys(self):
        return self.get_list_of_instruments()

    def get_list_of_instruments(self):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def get_roll_calendar(self, instrument_code):
        if self.is_code_in_data(instrument_code):
            return self._get_roll_calendar_without_checking(instrument_code)
        else:
            return rollCalendar.create_empty()

    def _get_roll_calendar_without_checking(self, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def __getitem__(self, instrument_code):
        return self.get_roll_calendar(instrument_code)

    def delete_roll_calendar(self, instrument_code, are_you_sure=False):
        self.log.label(instrument_code=instrument_code)

        if are_you_sure:
            if self.is_code_in_data(instrument_code):
                self._delete_roll_calendar_data_without_any_warning_be_careful(instrument_code)
                self.log.terse("Deleted roll calendar for %s" % instrument_code)

            else:
                ## doesn't exist anyway
                self.log.warn("Tried to delete roll calendar for non existent instrument code %s" % instrument_code)
        else:
            self.log.error("You need to call delete_roll_calendar with a flag to be sure")

    def _delete_roll_calendar_data_without_any_warning_be_careful(instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)

    def is_code_in_data(self, instrument_code):
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_roll_calendar(self, roll_calendar, instrument_code, ignore_duplication=False):

        self.log.label(instrument_code=instrument_code)

        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                raise self.log.warn("There is already %s in the data, you have to delete it first" % instrument_code)

        self._add_roll_calendar_without_checking_for_existing_entry(roll_calendar, instrument_code)

        self.log.terse("Added roll calendar for instrument %s" % instrument_code)

    def _add_roll_calendar_without_checking_for_existing_entry(self, roll_calendar, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_CALENDAR_ERROR)
