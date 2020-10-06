from syscore.dateutils import month_from_contract_letter
from sysdata.futures.contract_dates_and_expiries import contractDate
from sysdata.futures.rolls import contractDateWithRollParameters
from sysdata.futures.instruments import futuresInstrument
from sysdata.futures.trading_hours import manyTradingStartAndEnd

from sysdata.data import baseData
from copy import copy
import datetime

NO_ROLL_CYCLE_PASSED = object()


class futuresContract(object):
    """
    Define an individual futures contract

    This is a combination of an instrument_object and contract_date object

    """

    def __init__(self, instrument_object, contract_date_object, **kwargs):
        """
        futuresContract(futuresInstrument, contractDate)
        OR
        futuresContract("instrument_code", "yyyymm")

        :param instrument_object: str or futuresInstrument
        :param contract_date_object: contractDate or contractDateWithRollParameters or str
        """

        if isinstance(instrument_object, str):
            if isinstance(contract_date_object, str):
                # create a simple object
                self.instrument = futuresInstrument(instrument_object)
                self.contract_date = contractDate(contract_date_object)
            if isinstance(contract_date_object, list):
                if len(contract_date_object) == 1:
                    self.instrument = futuresInstrument(instrument_object)
                    self.contract_date = contractDate(contract_date_object[0])
                else:
                    self.instrument = futuresInstrument(instrument_object)
                    self.contract_date = [
                        contractDate(contract_date)
                        for contract_date in contract_date_object
                    ]

        else:
            self.instrument = instrument_object
            self.contract_date = contract_date_object

        self._is_empty = False
        self.params = kwargs

    def __repr__(self):
        return self.ident()

    def __eq__(self, other):
        if self.instrument_code != other.instrument_code:
            return False
        if self.date != other.date:
            return False
        return True

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
        return self.instrument_code + "/" + self.date

    def as_tuple(self):
        return self.instrument_code, self.date

    @property
    def currently_sampling(self):
        if self.params.get("currently_sampling", None) is None:
            self.params["currently_sampling"] = False

        return self.params["currently_sampling"]

    def sampling_on(self):
        self.params["currently_sampling"] = True

    def sampling_off(self):
        self.params["currently_sampling"] = False

    def as_dict(self):
        """
        Turn into a dict. We only include instrument_code from the instrument_object, the rest would be found elsewhere
           plus we have all the results from as_dict on the contract_date

        :return: dict
        """

        if self.empty():
            raise Exception("Can't create dict from empty object")

        contract_date_dict = self.contract_date.as_dict()
        instrument_dict = self.instrument.as_dict()
        contract_params_dict = self.params

        joint_dict = dict(
            contract_date_dict=contract_date_dict,
            instrument_dict=instrument_dict,
            contract_params=contract_params_dict,
        )

        return joint_dict

    @classmethod
    def create_from_dict(futuresContract, futures_contract_dict):
        """

        :param futures_contract_dict: The result of running .as_dict on a futuresContract.
        :return: futuresContract object
        """

        contract_date_dict = futures_contract_dict["contract_date_dict"]
        instrument_dict = futures_contract_dict["instrument_dict"]
        contract_params_dict = futures_contract_dict["contract_params"]

        contract_date_object = contractDate.create_from_dict(
            contract_date_dict)
        instrument_object = futuresInstrument.create_from_dict(instrument_dict)

        return futuresContract(
            instrument_object, contract_date_object, **contract_params_dict
        )

    @classmethod
    def simple(futuresContract, instrument_code, contract_date, **kwargs):
        DeprecationWarning(
            "futuresContract.simple(x,y) is deprecated, use futuresContract(x,y) instead"
        )
        return futuresContract(
            futuresInstrument(instrument_code),
            contractDate(
                contract_date,
                **kwargs))

    @property
    def instrument_code(self):
        return self.instrument.instrument_code

    def is_spread_contract(self):
        if isinstance(self.contract_date, list):
            if len(self.contract_date) > 1:
                return True
        else:
            return False

    @property
    def date(self):
        if self.is_spread_contract():
            return "_".join([str(x) for x in self.contract_date])
        else:
            return self.contract_date.contract_date

    @property
    def expiry_date(self):
        return self.contract_date.expiry_date

    @classmethod
    def approx_first_held_futuresContract_at_date(
        futuresContract, instrument_object, roll_parameters, reference_date
    ):
        try:
            first_contract_date = (
                roll_parameters.approx_first_held_contractDate_at_date(reference_date))
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(instrument_object, first_contract_date)

    @classmethod
    def approx_first_priced_futuresContract_at_date(
        futuresContract, instrument_object, roll_parameters, reference_date
    ):
        try:
            first_contract_date = (
                roll_parameters.approx_first_priced_contractDate_at_date(reference_date))
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(instrument_object, first_contract_date)

    def next_priced_contract(self):
        try:
            next_contract_date = self.contract_date.next_priced_contract()
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(self.instrument, next_contract_date)

    def previous_priced_contract(self):

        try:
            previous_contract_date = self.contract_date.previous_priced_contract()
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(self.instrument, previous_contract_date)

    def carry_contract(self):

        try:
            carry_contract = self.contract_date.carry_contract()
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(self.instrument, carry_contract)

    def next_held_contract(self):
        try:
            next_held_date = self.contract_date.next_held_contract()
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(self.instrument, next_held_date)

    def previous_held_contract(self):
        try:
            previous_held_date = self.contract_date.previous_held_contract()
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(self.instrument, previous_held_date)

    def new_contract_with_replaced_instrument_object(
            self, new_instrument_object):
        contract_date_object = self.contract_date

        return futuresContract(new_instrument_object, contract_date_object)


MAX_CONTRACT_SIZE = 10000


class listOfFuturesContracts(list):
    """
    Ordered list of futuresContracts
    """

    @classmethod
    def historical_price_contracts(
        listOfFuturesContracts,
        instrument_object,
        roll_parameters,
        first_contract_date,
        end_date=datetime.datetime.now(),
    ):
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

        first_contract = futuresContract(
            instrument_object, contractDateWithRollParameters(
                roll_parameters, first_contract_date), )

        assert end_date > first_contract.expiry_date

        current_held_contract = (
            futuresContract.approx_first_held_futuresContract_at_date(
                instrument_object, roll_parameters, end_date
            )
        )
        current_priced_contract = (
            futuresContract.approx_first_priced_futuresContract_at_date(
                instrument_object, roll_parameters, end_date
            )
        )
        current_carry_contract = current_held_contract.carry_contract()

        # these are all str thats okay
        last_contract_date = max(
            [
                current_held_contract.date,
                current_priced_contract.date,
                current_carry_contract.date,
            ]
        )

        list_of_contracts = [first_contract]

        # note the same instrument_object will be shared by all in the list so
        # we can modify it directly if needed
        date_still_valid = True
        current_contract = first_contract

        while date_still_valid:
            next_contract = current_contract.next_priced_contract()

            list_of_contracts.append(next_contract)

            if next_contract.date >= last_contract_date:
                date_still_valid = False
                # will now terminate
            if len(list_of_contracts) > MAX_CONTRACT_SIZE:
                raise Exception("Too many contracts - check your inputs")

            current_contract = next_contract

        return listOfFuturesContracts(list_of_contracts)

    def currently_sampling(self):
        contracts_currently_sampling = [
            contract for contract in self if contract.currently_sampling
        ]

        return listOfFuturesContracts(contracts_currently_sampling)

    def list_of_dates(self):
        # Return list of contract_date identifiers
        contract_dates = [contract.date for contract in self]
        return contract_dates

    def as_dict(self):
        contract_dates_keys = self.list_of_dates()
        contract_values = self

        contract_dict = dict([(key, value) for key, value in zip(
            contract_dates_keys, contract_values)])

        return contract_dict

    def difference(self, another_contract_list):
        return self._set_operation(
            another_contract_list,
            operation="difference")

    def _set_operation(self, another_contract_list, operation="difference"):
        """
        Equivalent to set(self).operation(set(another_contract_list))

        Since set will use __eq__ methods this will often fail, but we're happy to match equality if
          contract dates are the same

        :param another_contract_list:
        :param operation: str, one of intersection, union, difference
        :return: list of contracts that are in self but not in another contract_list
        """

        self_as_dict = self.as_dict()
        another_contract_list_as_dict = another_contract_list.as_dict()

        self_contract_dates = set(self_as_dict.keys())
        another_contract_list_dates = set(another_contract_list_as_dict.keys())

        try:
            operation_func = getattr(self_contract_dates, operation)
        except AttributeError:
            raise Exception("%s is not a valid set method" % operation)

        list_of_dates = operation_func(another_contract_list_dates)

        # turn back into contracts
        if operation == "difference" or operation == "intersect":
            list_of_contracts = [
                self_as_dict[contract_date] for contract_date in list_of_dates
            ]
        elif operation == "union":
            list_of_contracts_from_self = [
                self_as_dict[contract_date]
                for contract_date in list_of_dates
                if contract_date in self_as_dict.keys()
            ]
            list_of_contracts_from_other = [
                another_contract_list_as_dict[contract_date]
                for contract_date in list_of_dates
                if contract_date not in self_as_dict.keys()
            ]
            list_of_contracts = (
                list_of_contracts_from_other + list_of_contracts_from_self
            )

        else:
            raise Exception("%s not supported" % operation)

        return list_of_contracts


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

    def get_all_contract_objects_for_instrument_code(self, instrument_code):
        contract_dates_list = self.get_list_of_contract_dates_for_instrument_code(
            instrument_code)
        contract_objects_list = [
            self.get_contract_data(instrument_code, contract_date)
            for contract_date in contract_dates_list
        ]

        contract_objects_list = listOfFuturesContracts(contract_objects_list)

        return contract_objects_list

    def get_contract_data(self, instrument_code, contract_date):
        if self.is_contract_in_data(instrument_code, contract_date):
            return self._get_contract_data_without_checking(
                instrument_code, contract_date
            )
        else:
            return futuresContract.create_empty()

    def _get_contract_data_without_checking(
            self, instrument_code, contract_date):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def __getitem__(self, key_tuple):
        (instrument_code, contract_date) = key_tuple
        return self.get_contract_data(instrument_code, contract_date)

    def delete_contract_data(
            self,
            instrument_code,
            contract_date,
            are_you_sure=False):
        self.log.label(
            instrument_code=instrument_code,
            contract_date=contract_date)
        if are_you_sure:
            if self.is_contract_in_data(instrument_code, contract_date):
                self._delete_contract_data_without_any_warning_be_careful(
                    instrument_code, contract_date
                )
                self.log.terse(
                    "Deleted contract %s/%s" % (instrument_code, contract_date)
                )
            else:
                # doesn't exist anyway
                self.log.warn("Tried to delete non existent contract")
        else:
            self.log.error(
                "You need to call delete_contract_data with a flag to be sure"
            )

    def _delete_contract_data_without_any_warning_be_careful(
        self, instrument_code, contract_date
    ):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def delete_all_contracts_for_instrument(
        self, instrument_code, areyoureallysure=False
    ):
        if not areyoureallysure:
            raise Exception(
                "You have to be sure to delete all contracts for an instrument!"
            )

        list_of_dates = self.get_list_of_contract_dates_for_instrument_code(
            instrument_code
        )
        for contract_date in list_of_dates:
            self.delete_contract_data(
                instrument_code, contract_date, are_you_sure=True)

    def is_contract_in_data(self, instrument_code, contract_date):
        if contract_date in self.get_list_of_contract_dates_for_instrument_code(
                instrument_code):
            return True
        else:
            return False

    def add_contract_data(self, contract_object, ignore_duplication=False):

        instrument_code = contract_object.instrument_code
        contract_date = contract_object.date

        self.log.label(
            instrument_code=instrument_code,
            contract_date=contract_date)

        if self.is_contract_in_data(instrument_code, contract_date):
            if ignore_duplication:
                pass
            else:
                self.log.warn(
                    "There is already %s/%s in the data, you have to delete it first" %
                    (instrument_code, contract_date))
                return None

        self._add_contract_object_without_checking_for_existing_entry(
            contract_object)
        self.log.terse(
            "Added contract %s %s" %
            (instrument_code, contract_date))

    def _add_contract_object_without_checking_for_existing_entry(
            self, contract_object):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def get_actual_expiry_date_for_instrument_code_and_contract_date(
        self, instrument_code, contract_date
    ):
        contract_object = futuresContract(instrument_code, contract_date)

        return self.get_actual_expiry_date_for_contract(contract_object)

    def get_actual_expiry_date_for_contract(self, contract_object):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)

    def is_instrument_code_and_contract_date_okay_to_trade(
        self, instrument_code, contract_date
    ):
        contract_object = futuresContract(instrument_code, contract_date)
        result = self.is_contract_okay_to_trade(contract_object)

        return result

    def less_than_one_hour_of_trading_leg_for_instrument_code_and_contract_date(
            self, instrument_code, contract_date):
        contract_object = futuresContract(instrument_code, contract_date)
        result = self.less_than_one_hour_of_trading_leg_for_contract(
            contract_object)

        return result

    def is_contract_okay_to_trade(self, contract_object):
        trading_hours = self.get_trading_hours_for_contract(contract_object)
        trading_hours_checker = manyTradingStartAndEnd(trading_hours)

        return trading_hours_checker.okay_to_trade_now()

    def less_than_one_hour_of_trading_leg_for_contract(self, contract_object):
        trading_hours = self.get_trading_hours_for_contract(contract_object)
        trading_hours_checker = manyTradingStartAndEnd(trading_hours)

        return trading_hours_checker.less_than_one_hour_left()

    def get_trading_hours_for_instrument_code_and_contract_date(
        self, instrument_code, contract_date
    ):
        contract_object = futuresContract(instrument_code, contract_date)
        result = self.get_trading_hours_for_contract(contract_object)

        return result

    def get_trading_hours_for_contract(self, contract_object):
        raise NotImplementedError(USE_CHILD_CLASS_ERROR)
