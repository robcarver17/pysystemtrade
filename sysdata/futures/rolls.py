from bisect import bisect_left, bisect_right

import datetime
import pandas as pd
from copy import copy

from syscore.dateutils import contract_month_from_number, month_from_contract_letter
from sysdata.futures.contract_dates_and_expiries import contractDate, from_contract_numbers_to_contract_string, NO_DAY_PASSED, NO_EXPIRY_DATE_PASSED
from sysdata.data import baseData


EMPTY_ROLL_CYCLE_STRING=""

class rollCycle(object):
    """
    A cycle determining how one contract rolls to the next

    Only works with monthly contracts
    """

    def __init__(self, cyclestring):

        assert type(cyclestring) is str

        self.cyclestring = ''.join(sorted(cyclestring))
        self.cycle_as_list = [month_from_contract_letter(contract_letter)
                              for contract_letter in self.cyclestring]

        if cyclestring == EMPTY_ROLL_CYCLE_STRING:
            self._isempty = True
        else:
            self._isempty = False

    def empty(self):
        return self._isempty

    def __repr__(self):
        return self.cyclestring

    def as_list(self):
        """

        :return: list with int values referring to month numbers eg January =12 etc
        """
        return self.cycle_as_list

    def offset_month(self, current_month, offset):
        """
        Move a number of months in the expiry cycle

        :param current_month: Current month as a str
        :param offset: number of months to go forwards or backwards
        :return: new month as str
        """

        current_index = self.where_month(current_month)
        len_cycle = len(self.cyclestring)
        new_index = current_index+offset
        cycled_index = new_index % len_cycle

        return self.cyclestring[cycled_index]

    def next_month(self, current_month):
        """
        Move one month forward in expiry cycle

        :param current_month: Current month as a str
        :return: new month as str
        """

        return self.offset_month(current_month, 1)

    def previous_month(self, current_month):
        """
        Move one month back in expiry cycle

        :param current_month: Current month as a str
        :return: new month as str
        """

        return self.offset_month(current_month, -1)

    def where_month(self, current_month):
        """
        Return the index value (0 is first) of month in expiry

        :param current_month: month as str
        :return: int
        """
        self.check_is_month_in_rollcycle(current_month)

        return self.cyclestring.index(current_month)


    def month_is_first(self, current_month):
        """
        Is this the first month in the expiry cycle?

        :param current_month: month as str
        :return: bool
        """

        return self.where_month(current_month) == 0

    def month_is_last(self, current_month):
        """
        Is this the last month in the expiry cycle?

        :param current_month: month as str
        :return: bool
        """

        return self.where_month(current_month) == len(self.cyclestring) - 1

    def previous_year_month(self, year_value, month_str):
        """
        Returns a tuple (year, month: str)

        :param month_str: str
        :param year_value: int
        :return: tuple (int, str)
        """

        new_month_as_str = self.previous_month(month_str)
        if self.month_is_first(month_str):
            year_value = year_value -1

        return year_value, new_month_as_str

    def next_year_month(self, year_value, month_str):
        """
        Returns a tuple (year, month: str)

        :param month_str: str
        :param year_value: int
        :return: tuple (int, str)
        """

        new_month_as_str = self.next_month(month_str)
        if self.month_is_last(month_str):
            year_value = year_value + 1

        return year_value, new_month_as_str

    def yearmonth_inrollcycle_before_date(self, reference_date):
        """
        Returns a tuple (month,year) which is in this roll cycle; and which is just before reference_date

        :param reference_date: datetime.datetime
        :return: tuple (int, int)
        """

        relevant_year = reference_date.year
        relevant_month = reference_date.month
        roll_cycle_as_list = self.as_list()

        closest_month_index = bisect_left(roll_cycle_as_list, relevant_month)-1

        if closest_month_index==-1:
            # We are to the left of, or equal to the first month, go back one
            first_month_in_year_as_str = self.cyclestring[0]
            adjusted_year_int, adjusted_month_str = self.previous_year_month(relevant_year, first_month_in_year_as_str)
            adjusted_month_int = month_from_contract_letter(adjusted_month_str)
        else:
            adjusted_month_int = roll_cycle_as_list[closest_month_index]
            adjusted_year_int = relevant_year

        return (adjusted_year_int, adjusted_month_int)

    def yearmonth_inrollcycle_after_date(self, reference_date):
        """
        Returns a tuple (month,year) which is in this roll cycle; and which is just before reference_date

        :param reference_date: datetime.datetime
        :return: tuple (int, int)
        """

        relevant_year = reference_date.year
        relevant_month = reference_date.month

        roll_cycle_as_list = self.as_list()

        closest_month_index = bisect_right(roll_cycle_as_list, relevant_month)

        if closest_month_index==len(roll_cycle_as_list):
            ## fallen into the next year
            # go forward one from the last month
            last_month_in_year_as_str = self.cyclestring[-1]
            adjusted_year_int, adjusted_month_str = self.next_year_month( relevant_year, last_month_in_year_as_str)
            adjusted_month_int = month_from_contract_letter(adjusted_month_str)
        else:
            adjusted_month_int = roll_cycle_as_list[closest_month_index]
            adjusted_year_int = relevant_year

        return (adjusted_year_int, adjusted_month_int)



    def check_is_month_in_rollcycle(self, current_month):
        """
        Is current_month in our expiry cycle?

        :param current_month: month as str
        :return: bool
        """
        if current_month in self.cyclestring:
            return True
        else:
            raise Exception("%s not in cycle %s" % (current_month, self.cyclestring))



class rollParameters(object):
    """
    A rollParameters object contains information about roll cycles and how we hold contracts

    When combined with a contractDate we get a rollWithData which we can use to manipulate the contractDate
       according to the rules of rollParameters

    """

    def __init__(self, hold_rollcycle = EMPTY_ROLL_CYCLE_STRING, priced_rollcycle = EMPTY_ROLL_CYCLE_STRING,
                 roll_offset_day=0,
                 carry_offset=0, approx_expiry_offset = 0):
        """

        :param hold_rollcycle: The rollcycle which we actually want to hold, str
        :param priced_rollcycle: The entire rollcycle for which prices are available, str
        :param roll_offset_day: The day, relative to the expiry date, when we usually roll; int
        :param carry_offset: The number of contracts forward or backwards we look for to define carry in the priced roll cycle; int
        :param approx_expiry_offset: The offset, relative to the 1st of the contract month, when an expiry date usually occurs; int

        """


        self.hold_rollcycle = hold_rollcycle
        self.priced_rollcycle = priced_rollcycle
        self.roll_offset_day = roll_offset_day
        self.carry_offset = carry_offset
        self.approx_expiry_offset = approx_expiry_offset

        self._is_empty = False

    def __repr__(self):
        dict_rep = self.as_dict()
        str_rep = ", ".join(["%s:%s" % (key, str(dict_rep[key])) for key in dict_rep.keys()])
        return "Rollcycle parameters "+str_rep

    @property
    def priced_rollcycle(self):
        return self._priced_rollcycle

    @priced_rollcycle.setter
    def priced_rollcycle(self, priced_rollcycle):
        self._priced_rollcycle = rollCycle(priced_rollcycle)

    @property
    def hold_rollcycle(self):
        return self._hold_rollcycle

    @hold_rollcycle.setter
    def hold_rollcycle(self, hold_rollcycle):
        self._hold_rollcycle = rollCycle(hold_rollcycle)

    def check_for_price_cycle(self):
        self.check_for_named_rollcycle("priced_rollcycle")

    def check_for_hold_cycle(self):
        self.check_for_named_rollcycle("hold_rollcycle")

    def check_for_named_rollcycle(self, rollcycle_name):
        """
        Check to see if a rollcycle is empty

        :param rollcycle_name: str, attribute of self, eithier 'priced_rollcycle' or 'hold_rollcycle'
        :return: nothing or exception
        """

        rollcycle_to_check = getattr(self, rollcycle_name)
        if rollcycle_to_check.empty():
            raise Exception("You need a defined %s to do this!" % rollcycle_name)

    @classmethod
    def create_empty(rollData):
        futures_instrument_roll_data = rollData()
        futures_instrument_roll_data._is_empty = True

        return futures_instrument_roll_data

    @classmethod
    def create_from_dict(rollData, roll_data_dict):

        futures_instrument_roll_data = rollData(**roll_data_dict)

        return futures_instrument_roll_data

    def as_dict(self):

        if self.empty():
            raise Exception("Can't create dict from empty object")

        return dict(hold_rollcycle = self.hold_rollcycle.cyclestring, priced_rollcycle = self.priced_rollcycle.cyclestring,
                    roll_offset_day = self.roll_offset_day,  carry_offset = self.carry_offset,
                    approx_expiry_offset = self.approx_expiry_offset)

    def empty(self):
        return self._is_empty


    def approx_first_held_contractDate_at_date(self, reference_date):
        """
        What contract would be holding on first_date?

        Returns a contractDate object with a date after first_date, taking into account RollOffsetDays
          as well as the held roll cycle.

        :param reference_date:
        :return: contractDate object
        """
        self.check_for_hold_cycle()

        self.check_for_price_cycle()

        current_date_as_contract_with_roll_data = self._approx_first_contractDate_at_date(reference_date, "hold_rollcycle")

        return current_date_as_contract_with_roll_data

    def approx_first_priced_contractDate_at_date(self, reference_date):
        """
        What contract would be pricing on first_date?

        Returns a contractDate object with a date after first_date, taking into account RollOffsetDays
          as well as the priced roll cycle.

        :param reference_date:
        :return: contractDate object
        """
        self.check_for_price_cycle()

        current_date_as_contract_with_roll_data = self._approx_first_contractDate_at_date(reference_date, "priced_rollcycle")

        return current_date_as_contract_with_roll_data

    def _approx_first_contractDate_at_date(self, reference_date, rollcycle_name):
        """
        What contract would be pricing or holding on reference_date?

        Returns a contractDate object with a date after reference_date, taking into account RollOffsetDays
          as well as the priced roll cycle.

        :param reference_date: datetime
        :return: contractDate object
        """

        # first held contract after current date
        roll_cycle = getattr(self, rollcycle_name)

        # For example suppose the reference date is 20190101, and the expiry offset is 15
        #    plus the roll offset is -90 (we want to roll ~ 3 months in advance of the expiry)
        #    The contract expires on the 16th of each month
        #    We want to roll 90 days ahead of that
        #    With thanks to https://github.com/tgibson11 for helping me get this right

        adjusted_date = reference_date - pd.DateOffset(days = (self.roll_offset_day + self.approx_expiry_offset))

        relevant_year_int, relevant_month_int = roll_cycle.yearmonth_inrollcycle_after_date(adjusted_date)

        current_date_as_contract_with_roll_data = contractDateWithRollParameters.contract_date_from_numbers(self, relevant_year_int,
                                                                                                            relevant_month_int,
                                                                                                            approx_expiry_offset=self.approx_expiry_offset)

        return current_date_as_contract_with_roll_data



class contractDateWithRollParameters(contractDate):
    """
    Roll data plus a specific contract date means we can do things like iterate the roll cycle etc

    """

    def __init__(self, roll_parameters, *args, inherit_expiry_offset = True, **kwargs):
        """

        :param roll_parameters: rollParameters

        Additional arguments are passed to contractDate
        """

        if inherit_expiry_offset:
            if "approx_expiry_offset" in kwargs.keys():
                #Ignoring passed approx_expiry_offset, and using one in rolldata
                pass

            kwargs["approx_expiry_offset"] = roll_parameters.approx_expiry_offset

        super().__init__(*args, **kwargs)
        self.roll_parameters = roll_parameters


    @classmethod
    def contract_date_from_numbers(contractDateWithRollData, rolldata_object,
                            new_year_number, new_month_number, new_day_number=NO_DAY_PASSED, **kwargs):

        contract_string = from_contract_numbers_to_contract_string(new_year_number, new_month_number, new_day_number)

        contract_date_with_roll_data_object = contractDateWithRollData(rolldata_object, contract_string, **kwargs)

        return contract_date_with_roll_data_object

    @classmethod
    def create_from_dict(contractDateWithRollData, contract_date_dict, roll_data_dict):

        print("**")
        print(contract_date_dict)
        if "expiry_date" in contract_date_dict.keys():
            expiry_date = contract_date_dict['expiry_date']
            if expiry_date == "":
                expiry_date = NO_EXPIRY_DATE_PASSED
        else:
            expiry_date = NO_EXPIRY_DATE_PASSED

        print(expiry_date)

        if "approx_expiry_offset" in contract_date_dict.keys():
            approx_expiry_offset = contract_date_dict['approx_expiry_offset']
        else:
            approx_expiry_offset = 0

        roll_parameters = rollParameters.create_from_dict(roll_data_dict)

        return contractDateWithRollData(roll_parameters, contract_date_dict['contract_date'], expiry_date=expiry_date)


    def _check_valid_date_in_named_rollcycle(self, rollcycle_name):

        self.roll_parameters.check_for_named_rollcycle(rollcycle_name)
        relevant_rollcycle = getattr(self.roll_parameters, rollcycle_name)
        rollcycle_str = relevant_rollcycle.cyclestring

        current_month = self.letter_month()

        if not current_month in rollcycle_str:
            raise Exception("ContractDate with %s roll cycle, month %s must be in cycle %s" % (rollcycle_name,
                                                                                                   current_month,
                                                                                                   rollcycle_str))

    def _check_valid_date_in_priced_rollcycle(self):
        self._check_valid_date_in_named_rollcycle("priced_rollcycle")

    def _check_valid_date_in_held_rollcycle(self):
        self._check_valid_date_in_named_rollcycle("held_rollcycle")

    def _iterate_contract(self, direction_function_name, rollcycle_name):
        """
        Used for going backward or forwards

        :param direction_function_name: str, attribute method of a roll cycle, eithier 'next_year_month' or 'previous_year_month'
        :param rollcycle_name: str, attribute method of self.roll_parameters, eithier 'priced_rollcycle' or 'held_rollcycle'
        :return: new contractDate object
        """

        self._check_valid_date_in_named_rollcycle(rollcycle_name)

        rollcycle_to_use = getattr(self.roll_parameters, rollcycle_name)
        direction_function = getattr(rollcycle_to_use, direction_function_name)

        current_month_str = self.letter_month()
        current_year_int = self.year()

        new_year_int, new_month_str = direction_function(current_year_int, current_month_str)
        new_month_int = month_from_contract_letter(new_month_str)

        if self._only_has_month:
            new_day_number = 0
        else:
            new_day_number=self.day()

        ## we don't pass expiry date as that will change
        return contractDateWithRollParameters.contract_date_from_numbers(self.roll_parameters,
                                                                         new_year_int, new_month_int, new_day_number = new_day_number,
                                                                         approx_expiry_offset = self.roll_parameters.approx_expiry_offset)


    def next_priced_contract(self):
        return self._iterate_contract("next_year_month", "priced_rollcycle")


    def previous_priced_contract(self):
        return self._iterate_contract("previous_year_month", "priced_rollcycle")

    def next_held_contract(self):
        return self._iterate_contract("next_year_month", "hold_rollcycle")


    def previous_held_contract(self):
        return self._iterate_contract("previous_year_month", "hold_rollcycle")

    def carry_contract(self):
        if self.roll_parameters.carry_offset == -1:
            return self.previous_priced_contract()
        elif self.roll_parameters.carry_offset == 1:
            return self.next_priced_contract()
        else:
            raise Exception("carry_offset needs to be +1 or -1")

    def want_to_roll(self):
        return self.expiry_date+ datetime.timedelta(days = self.roll_parameters.roll_offset_day)

    def get_unexpired_contracts_from_now_to_contract_date(self):
        """
        Returns all the unexpired contracts between now and the contract date

        :return: list of contractDate
        """

        datetime_now = datetime.datetime.now()
        contract_dates = []
        current_contract = copy(self)

        while current_contract.as_date() >= datetime_now:
            contract_dates.append(current_contract)
            current_contract = current_contract.previous_priced_contract()

        return contract_dates

USE_CHILD_CLASS_ROLL_PARAMS_ERROR = "You need to use a child class of rollParametersData"

class rollParametersData(baseData):
    """
    Read and write data class to get roll data for a given instrument

    We'd inherit from this class for a specific implementation

    """

    def __repr__(self):
        return "rollParametersData base class - DO NOT USE"

    def keys(self):
        return self.get_list_of_instruments()

    def get_list_of_instruments(self):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_PARAMS_ERROR)

    def get_roll_parameters(self, instrument_code):
        if self.is_code_in_data(instrument_code):
            return self._get_roll_parameters_without_checking(instrument_code)
        else:
            return rollParameters.create_empty()

    def _get_roll_parameters_without_checking(self, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_PARAMS_ERROR)

    def __getitem__(self, instrument_code):
        return self.get_roll_parameters(instrument_code)

    def delete_roll_parameters(self, instrument_code, are_you_sure=False):
        self.log.label(instrument_code=instrument_code)

        if are_you_sure:
            if self.is_code_in_data(instrument_code):
                self._delete_roll_parameters_data_without_any_warning_be_careful(instrument_code)
                self.log.terse("Deleted roll parameters for %s" % instrument_code)

            else:
                ## doesn't exist anyway
                self.log.warn("Tried to delete roll parameters for non existent instrument code %s" % instrument_code)
        else:
            self.log.error("You need to call delete_roll_parameters with a flag to be sure")

    def _delete_roll_parameters_data_without_any_warning_be_careful(instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_PARAMS_ERROR)

    def is_code_in_data(self, instrument_code):
        if instrument_code in self.get_list_of_instruments():
            return True
        else:
            return False

    def add_roll_parameters(self, roll_parameters, instrument_code, ignore_duplication=False):

        self.log.label(instrument_code=instrument_code)

        if self.is_code_in_data(instrument_code):
            if ignore_duplication:
                pass
            else:
                raise self.log.warn("There is already %s in the data, you have to delete it first" % instrument_code)

        self._add_roll_parameters_without_checking_for_existing_entry(roll_parameters, instrument_code)

        self.log.terse("Added roll parameters for instrument %s" % instrument_code)

    def _add_roll_parameters_without_checking_for_existing_entry(self, roll_parameters, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ROLL_PARAMS_ERROR)

