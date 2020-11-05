from syscore.objects import arg_not_supplied
from sysobjects.contract_dates_and_expiries import contractDate
from sysdata.futures.rolls import contractDateWithRollParameters
from sysobjects.instruments import futuresInstrument
from dataclasses import  dataclass

import datetime

NO_ROLL_CYCLE_PASSED = object()

@dataclass
class parametersForFuturesContract:
    sampling: bool = False

    def as_dict(self) -> dict:
        keys = self.__dataclass_fields__.keys()
        self_as_dict = dict([(key, getattr(self, key)) for key in keys])

        return self_as_dict

    @classmethod
    def from_dict(parametersForFuturesContract, input_dict):
        keys = parametersForFuturesContract.__dataclass_fields__.keys()
        args_list = [input_dict.get(key, None) for key in keys ]
        args_list = [value for value in args_list if value is not None]

        return parametersForFuturesContract(*args_list)

class futuresContract(object):
    """
    Define an individual futures contract

    This is a combination of an instrument_object and contract_date object

    """

    def __init__(self, instrument_object: futuresInstrument, contract_date_object: contractDate,
                 parameter_object: parametersForFuturesContract = arg_not_supplied):
        """
        futuresContract(futuresInstrument, contractDate)
        OR
        futuresContract("instrument_code", "yyyymm")

        :param instrument_object: str or futuresInstrument
        :param contract_date_object: contractDate or contractDateWithRollParameters or str
        """

        instrument_object, contract_date_object = _resolve_args_for_futures_contract(instrument_object, contract_date_object)

        self._instrument = instrument_object
        self._contract_date = contract_date_object

        if parameter_object is arg_not_supplied:
            parameter_object = parametersForFuturesContract()

        self._is_empty = False
        self._params = parameter_object

    @property
    def instrument(self):
        return self._instrument

    @property
    def contract_date(self):
        return self._contract_date

    @property
    def params(self):
        return self._params

    def __repr__(self):
        return self.key()

    def __eq__(self, other):
        if self.instrument_code != other.instrument_code:
            return False
        if self.date != other.date:
            return False
        return True

    @classmethod
    ## CLASIER WAY?
    def create_empty(futuresContract):
        fake_instrument = futuresInstrument("EMPTY")
        fake_contract_date = contractDate("150001")

        futures_contract = futuresContract(fake_instrument, fake_contract_date)
        futures_contract._is_empty = True

        return futures_contract

    def empty(self):
        return self._is_empty

    def ident(self):
        ## REPLACE WITH KEY WHERE USED?
        return self.key()

    def key(self):
        return self.instrument_code + "/" + self.date

    def as_tuple(self):
        ## USED WHERE?
        return self.instrument_code, self.date

    @property
    def currently_sampling(self):
        return self.params.sampling

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
        contract_params_dict = self.params.as_dict()

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
        parameter_object = parametersForFuturesContract.from_dict(contract_params_dict)

        return futuresContract(
            instrument_object, contract_date_object, parameter_object= parameter_object
        )

    @classmethod
    ## USED AT ALL?
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

    ## SHOULD BE IN CONTRACT DATE?
    ## SHOULD HAVE CONTRACT DATE AS A SEPERATE OBJECT WHICH CAN BE A SPREAD?

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
        ## WHERE USED, SEEMS SHOULD BE A SEPERATE FUNCTION
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
        ## WHERE USED, SEEMS SHOULD BE A SEPERATE FUNCTION
        ## OR EXPLICIT FUTURES CONTRACT OBJECT WITH ROLL DATA
        try:
            first_contract_date = (
                roll_parameters.approx_first_priced_contractDate_at_date(reference_date))
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(instrument_object, first_contract_date)

    def next_priced_contract(self):
        ## WHERE USED, SEEMS SHOULD BE A SEPERATE FUNCTION
        ## OR EXPLICIT FUTURES CONTRACT OBJECT WITH ROLL DATA

        try:
            next_contract_date = self.contract_date.next_priced_contract()
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(self.instrument, next_contract_date)

    def previous_priced_contract(self):
        ## WHERE USED, SEEMS SHOULD BE A SEPERATE FUNCTION
        ## OR EXPLICIT FUTURES CONTRACT OBJECT WITH ROLL DATA

        try:
            previous_contract_date = self.contract_date.previous_priced_contract()
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(self.instrument, previous_contract_date)

    def carry_contract(self):
        ## WHERE USED, SEEMS SHOULD BE A SEPERATE FUNCTION
        ## OR EXPLICIT FUTURES CONTRACT OBJECT WITH ROLL DATA

        try:
            carry_contract = self.contract_date.carry_contract()
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(self.instrument, carry_contract)

    def next_held_contract(self):
        ## WHERE USED, SEEMS SHOULD BE A SEPERATE FUNCTION
        ## OR EXPLICIT FUTURES CONTRACT OBJECT WITH ROLL DATA

        try:
            next_held_date = self.contract_date.next_held_contract()
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(self.instrument, next_held_date)

    def previous_held_contract(self):
        ## WHERE USED, SEEMS SHOULD BE A SEPERATE FUNCTION
        ## OR EXPLICIT FUTURES CONTRACT OBJECT WITH ROLL DATA

        try:
            previous_held_date = self.contract_date.previous_held_contract()
        except AttributeError:
            raise Exception(
                "You can only do this if contract_date_object is contractDateWithRollParameters"
            )

        return futuresContract(self.instrument, previous_held_date)

    def new_contract_with_replaced_instrument_object(
            self, new_instrument_object):
        ## WHERE USED
        contract_date_object = self.contract_date

        return futuresContract(new_instrument_object, contract_date_object)

def _resolve_args_for_futures_contract(instrument_object, contract_date_object) -> tuple:

    instrument_is_str = isinstance(instrument_object, str)
    contract_date_is_str = isinstance(contract_date_object, str)

    ## NEED A MORE SATISFYING WAY OF DOING THIS...
    contract_date_is_list = isinstance(contract_date_object, list)

    if instrument_is_str and  contract_date_is_str:
        return _resolve_args_where_both_are_str(instrument_object, contract_date_object)

    if instrument_is_str and contract_date_is_list:
        return _resolve_args_where_instrument_str_and_contract_date_is_list(instrument_object, contract_date_object)

    return instrument_object, contract_date_object

def _resolve_args_where_both_are_str(instrument_object_str, contract_date_object_str):
    # create a simple object
    instrument_object = futuresInstrument(instrument_object_str)
    contract_date_object = contractDate(contract_date_object_str)

    return instrument_object, contract_date_object


def _resolve_args_where_instrument_str_and_contract_date_is_list(instrument_object, contract_date_object_list):
    instrument_object = futuresInstrument(instrument_object)
    if len(contract_date_object_list) == 1:
        contract_date_object = contractDate(contract_date_object_list[0])
    else:
        contract_date_object = [
            contractDate(contract_date)
            for contract_date in contract_date_object_list
        ]

    return instrument_object, contract_date_object


MAX_CONTRACT_SIZE = 10000


class listOfFuturesContracts(list):
    """
    Ordered list of futuresContracts
    """

    @classmethod
    ## LOT OF PARAMTERS HERE!
    ## THIS FUNCTION TOO LARGE
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

    ## CHECK WHERE USED...
    def currently_sampling(self):
        contracts_currently_sampling = [
            contract for contract in self if contract.currently_sampling
        ]

        return listOfFuturesContracts(contracts_currently_sampling)

    def list_of_dates(self):
        ## CHECK WHERE USED...
        # Return list of contract_date identifiers
        contract_dates = [contract.date for contract in self]
        return contract_dates

    def as_dict(self):
        ## CHECK WHERE USED...
        contract_dates_keys = self.list_of_dates()
        contract_values = self

        contract_dict = dict([(key, value) for key, value in zip(
            contract_dates_keys, contract_values)])

        return contract_dict

    def difference(self, another_contract_list):
        ## CHECK WHERE USED...
        return self._set_operation(
            another_contract_list,
            operation="difference")

    def _set_operation(self, another_contract_list, operation="difference"):
        ### FUNCTION TO OBIG
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



