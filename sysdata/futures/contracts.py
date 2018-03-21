from syscore.dateutils import month_from_contract_letter
from sysdata.futures.contract_dates_and_expiries import contractDate
from sysdata.futures.rolls import contractDateWithRollParameters
from sysdata.futures.instruments import futuresInstrument
from sysdata.data import baseData
from copy import copy
import datetime

NO_ROLL_CYCLE_PASSED = object()


class futuresContract(object):
    """
    Define an individual futures contract

    This is a combination of an instrument_object and contract_date object

    """
    def __init__(self, instrument_object, contract_date_object):
        """

        :param instrument_object:
        :param contract_date_object: contractDate or contractDateWithRollParameters
        """

        self.instrument = instrument_object
        self.contract_date = contract_date_object
        self._is_empty = False


    def __repr__(self):
        return self.ident()

    @classmethod
    def create_empty(futuresContract):
        fake_instrument = futuresInstrument("EMPTY")
        fake_contract_date = contractDate("150001")

        futures_contract = futuresContract(fake_instrument, fake_contract_date)
        futures_contract._is_empty = True

        return futures_contract

    def empty(self):
        return self._is_empty

    def ident(self):
        return self.instrument_code + "/"+ self.date

    def as_tuple(self):
        return self.instrument_code, self.date

    def as_dict(self):
        """
        Turn into a dict. We only include instrument_code from the instrument_object, the rest would be found elsewhere
           plus we have all the results from as_dict on the contract_date

        :return: dict
        """

        if self.empty():
            raise Exception("Can't create dict from empty object")

        contract_date_dict = self.contract_date.as_dict()
        contract_date_dict['instrument_code'] = self.instrument_code

        return contract_date_dict

    @classmethod
    def create_from_dict_with_instrument_dict(futuresContract, instrument_dict, futures_contract_dict):
        """

        :param instrument_dict: The result of running .as_dict on a futuresInstrument
        :param futures_contract_dict: The result of running .as_dict on a futuresContract.
        :return: futuresContract object
        """

        # If we run as_dict on a futuresContract we get the instrument_code
        assert instrument_dict['instrument_code'] == futures_contract_dict['instrument_code']

        contract_date_dict = copy(futures_contract_dict)
        contract_date_dict.pop('instrument_code') # not used

        contract_date_object = contractDate.create_from_dict(contract_date_dict)
        instrument_object = futuresInstrument.create_from_dict(instrument_dict)

        return futuresContract(instrument_object, contract_date_object)

    @classmethod
    def create_from_dict(futuresContract, futures_contract_dict):
        """

        :param futures_contract_dict: The result of running .as_dict on a futuresContract.
        :return: futuresContract object
        """

        contract_date_dict = copy(futures_contract_dict)
        instrument_code = contract_date_dict.pop('instrument_code')

        # We just do a 'bare' instrument with only a code
        instrument_dict = dict(instrument_code = instrument_code)

        contract_date_object = contractDate.create_from_dict(contract_date_dict)
        instrument_object = futuresInstrument.create_from_dict(instrument_dict)

        return futuresContract(instrument_object, contract_date_object)

    @classmethod
    def create_from_dict_with_rolldata(futuresContract, futures_contract_dict, roll_data_dict):
        """

        :param futures_contract_dict: The result of running .as_dict on a futuresContract.
        :param roll_data_dict: A roll data dict
        :return: futuresContract object
        """

        contract_date_dict = copy(futures_contract_dict)
        instrument_code = contract_date_dict.pop('instrument_code')

        # We just do a 'bare' instrument with only a code
        instrument_dict = dict(instrument_code = instrument_code)

        contract_date_with_rolldata_object = contractDateWithRollParameters.create_from_dict(contract_date_dict, roll_data_dict)
        instrument_object = futuresInstrument.create_from_dict(instrument_dict)

        return futuresContract(instrument_object, contract_date_with_rolldata_object)


    @classmethod
    def simple(futuresContract, instrument_code, contract_date, **kwargs):

        return futuresContract(futuresInstrument(instrument_code), contractDate(contract_date, **kwargs))


    @classmethod
    def identGivenCodeAndContractDate(futuresContract, instrument_code, contract_date):
        """
        Return an identification given a code and contract date

        :param instrument_code: str
        :param contract_date: str, following contract date rules
        :return: str
        """

        futures_contract = futuresContract.simple(instrument_code, contract_date)

        return futures_contract.ident()

    @property
    def instrument_code(self):
        return self.instrument.instrument_code

    @property
    def date(self):
        return self.contract_date.contract_date

    @property
    def expiry_date(self):
        return self.contract_date.expiry_date

    @classmethod
    def approx_first_held_futuresContract_at_date(futuresContract, instrument_object, roll_parameters, reference_date):
        try:
            first_contract_date = roll_parameters.approx_first_held_contractDate_at_date(reference_date)
        except AttributeError:
            raise Exception("You can only do this if contract_date_object is contractDateWithRollParameters")

        return futuresContract(instrument_object, first_contract_date)

    @classmethod
    def approx_first_priced_futuresContract_at_date(futuresContract, instrument_object, roll_parameters, reference_date):
        try:
            first_contract_date = roll_parameters.approx_first_priced_contractDate_at_date(reference_date)
        except AttributeError:
            raise Exception("You can only do this if contract_date_object is contractDateWithRollParameters")

        return futuresContract(instrument_object, first_contract_date)


    def next_priced_contract(self):
        try:
            next_contract_date = self.contract_date.next_priced_contract()
        except AttributeError:
            raise Exception("You can only do this if contract_date_object is contractDateWithRollParameters")

        return futuresContract(self.instrument, next_contract_date)


    def previous_priced_contract(self):

        try:
            previous_contract_date = self.contract_date.previous_priced_contract()
        except AttributeError:
            raise Exception("You can only do this if contract_date_object is contractDateWithRollParameters")

        return futuresContract(self.instrument, previous_contract_date)

    def carry_contract(self):

        try:
            carry_contract = self.contract_date.carry_contract()
        except AttributeError:
            raise Exception("You can only do this if contract_date_object is contractDateWithRollParameters")

        return futuresContract(self.instrument, carry_contract)

    def next_held_contract(self):
        try:
            next_held_date = self.contract_date.next_held_contract()
        except AttributeError:
            raise Exception("You can only do this if contract_date_object is contractDateWithRollParameters")

        return futuresContract(self.instrument, next_held_date)

    def previous_held_contract(self):
        try:
            previous_held_date = self.contract_date.previous_held_contract()
        except AttributeError:
            raise Exception("You can only do this if contract_date_object is contractDateWithRollParameters")

        return futuresContract(self.instrument, previous_held_date)


MAX_CONTRACT_SIZE = 10000

class listOfFuturesContracts(list):
    """
    Ordered list of futuresContracts
    """

    @classmethod
    def historical_price_contracts(listOfFuturesContracts, instrument_object, roll_parameters, first_contract_date,
                                   end_date=datetime.datetime.now()):
        """
        We want to get all the contracts that fit in the roll cycle, bearing in mind the RollOffsetDays (in roll_parameters)
          So for example suppose we want all contracts since 1st January 1980, to the present day, for
          Eurodollar; where the rollcycle = "HMUZ" (quarterly IMM) and where the rollOffSetDays is 1100
          (we want to be around 3 years in the future; eg 12 contracts). If it's current 1st January 2018
          then we'd get all contracts with expiries between 1st January 1980 to approx 1st January 2021

        This uses the 'priceRollCycle' rollCycle in instrument_object, which is a superset of the heldRollCycle


        :param instrument_object: An instrument object
        :param roll_parameters: rollParameters
        :param start_date: The first contract date, 'eg yyyymm'
        :param end_date: The date when we want to stop getting data, defaults to today

        :return: list of futuresContracts
        """

        first_contract = futuresContract(instrument_object, contractDateWithRollParameters(roll_parameters, first_contract_date))

        assert end_date > first_contract.expiry_date

        current_held_contract = futuresContract.approx_first_held_futuresContract_at_date(instrument_object, roll_parameters,
                                                                                              end_date)
        current_priced_contract = futuresContract.approx_first_priced_futuresContract_at_date(instrument_object, roll_parameters,
                                                                                              end_date)
        current_carry_contract = current_held_contract.carry_contract()

        # these are all str thats okay
        last_contract_date = max([current_held_contract.date, current_priced_contract.date, current_carry_contract.date])

        list_of_contracts = [first_contract]

        ## note the same instrument_object will be shared by all in the list so we can modify it directly if needed
        date_still_valid = True
        current_contract = first_contract

        while date_still_valid:
            next_contract = current_contract.next_priced_contract()

            list_of_contracts.append(next_contract)

            if next_contract.date >= last_contract_date:
                date_still_valid = False
                # will now terminate
            if len(list_of_contracts)>MAX_CONTRACT_SIZE:
                raise Exception("Too many contracts - check your inputs")

            current_contract = next_contract

        return listOfFuturesContracts(list_of_contracts)


USE_CHILD_CLASS_ERROR = "You need to use a child class of futuresContractData"
ContractNotFound = Exception()

class futuresContractData(baseData):
    """
    Read and write data class to get futures contract data

    We'd inherit from this class for a specific implementation

    We store instrument code, and contract date data (date, expiry, roll cycle)

    If you want more information about a given instrument you have to read it in using futuresInstrumentData
    """

    def __repr__(self):
        return "Individual futures contract data - DO NOT USE"

    def get_list_of_contract_dates_for_instrument_code(self, instrument_code):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_contract_data(self, instrument_code, contract_date):
        if self.is_contract_in_data(instrument_code, contract_date):
            return self._get_contract_data_without_checking(instrument_code, contract_date)
        else:
            return futuresContract.create_empty()

    def _get_contract_data_without_checking(self, instrument_code, contract_date):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def __getitem__(self, key_tuple):
        (instrument_code, contract_date) = key_tuple
        return self.get_contract_data(instrument_code, contract_date)

    def delete_contract_data(self, instrument_code, contract_date, are_you_sure=False):
        self.log.label(instrument_code=instrument_code, contract_date=contract_date)
        if are_you_sure:
            if self.is_contract_in_data(instrument_code, contract_date):
                self._delete_contract_data_without_any_warning_be_careful(instrument_code, contract_date)
                self.log.terse("Deleted contract %s/%s" % (instrument_code, contract_date))
            else:
                ## doesn't exist anyway
                self.log.warn("Tried to delete non existent contract")
        else:
            self.log.error("You need to call delete_contract_data with a flag to be sure")

    def _delete_contract_data_without_any_warning_be_careful(self, instrument_code, contract_date):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def is_contract_in_data(self, instrument_code, contract_date):
        if contract_date in self.get_list_of_contract_dates_for_instrument_code(instrument_code):
            return True
        else:
            return False

    def add_contract_data(self, contract_object, ignore_duplication=False):

        instrument_code = contract_object.instrument_code
        contract_date = contract_object.contract_date

        self.log.label(instrument_code=instrument_code, contract_date=contract_date)

        if self.is_contract_in_data(instrument_code, contract_date):
            if ignore_duplication:
                pass
            else:
                self.log.warn("There is already %s/%s in the data, you have to delete it first" % instrument_code, contract_date)

        self._add_contract_object_without_checking_for_existing_entry(contract_object)
        self.log.terse("Added contract %s %s" % (instrument_code, contract_date))

    def _add_contract_object_without_checking_for_existing_entry(self, contract_object):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

