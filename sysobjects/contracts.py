from dataclasses import  dataclass

from syscore.objects import arg_not_supplied, missing_contract

from syslogdiag.log import logger

from sysobjects.contract_dates_and_expiries import contractDate, expiryDate
from sysobjects.instruments import futuresInstrument



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


def contract_key_from_code_and_id(instrument_code, contract_id):
    contract = contract_from_code_and_id(instrument_code, contract_id)
    return contract.key


def contract_from_code_and_id(instrument_code, contract_id):
    return futuresContract(instrument_code, contract_id)

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

        if parameter_object is arg_not_supplied:
            parameter_object = parametersForFuturesContract()

        self._instrument = instrument_object
        self._contract_date = contract_date_object
        self._params = parameter_object


    def specific_log(self, log):
        new_log = log.setup(instrument_code = self.instrument_code, contract_date = self.date_str)

        return new_log

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
        return self.key

    def __eq__(self, other):
        instruments_match = self.instrument == other.instrument
        contracts_match = self.date_str == other.date_str

        if instruments_match and contracts_match:
            return True
        else:
            return False

    @property
    def key(self):
        return get_contract_key_from_code_and_id(self.instrument_code, self.date_str)

    @property
    def currently_sampling(self):
        return self.params.sampling

    def sampling_on(self):
        self.params.sampling = True

    def sampling_off(self):
        self.params.sampling = False

    def log(self, log: logger):
        return log.setup(instrument_code =self.instrument_code, contract_date = self.date_str)

    def as_dict(self):
        """
        Turn into a dict. We only include instrument_code from the instrument_object, the rest would be found elsewhere
           plus we have all the results from as_dict on the contract_date

        :return: dict
        """

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

    @property
    def instrument_code(self):
        return self.instrument.instrument_code

    @property
    def date_str(self):
        return self.contract_date.date_str

    @property
    def date(self):
        return self.contract_date.as_date

    @property
    def expiry_date(self):
        return self.contract_date.expiry_date

    def update_expiry_date(self, new_expiry_date: expiryDate):
        self.contract_date.update_expiry_date(new_expiry_date)

    def is_spread_contract(self):
        return self.contract_date.is_spread_contract

    def new_contract_with_replaced_instrument_object(
            self, new_instrument_object):
        contract_date_object = self.contract_date
        params = self.params

        return futuresContract(new_instrument_object, contract_date_object, parameter_object=params)

    def new_contract_with_first_contract_date(self):
        new_contract_date_object = self.contract_date.first_contract_as_contract_date()

        return self.new_contract_with_replaced_contract_date_object(new_contract_date_object)

    def new_contract_with_replaced_contract_date_object(self, new_contract_date_object):
        instrument_object = self.instrument
        params = self.params

        return futuresContract(instrument_object, new_contract_date_object, params)

def _resolve_args_for_futures_contract(instrument_object, contract_date_object) -> tuple:

    if isinstance(instrument_object, str):
        instrument_object = futuresInstrument(instrument_object)

    if isinstance(contract_date_object, list) or isinstance(contract_date_object, str) \
            or isinstance(contract_date_object, dict):
        contract_date_object = contractDate(contract_date_object)

    return instrument_object, contract_date_object


def key_contains_instrument_code(contract_key, instrument_code):
    key_instrument_code, contract_id = get_code_and_id_from_contract_key(contract_key)
    if key_instrument_code == instrument_code:
        return True
    else:
        return False

def get_contract_key_from_code_and_id(instrument_code, contract_id):
    return instrument_code + "/" + contract_id

def get_code_and_id_from_contract_key(contract_key):
    return contract_key.split("/")


class listOfFuturesContracts(list):
    """
    List of futuresContracts
    """
    def unique_list_of_instrument_codes(self):
        list_of_instruments = [
            contract.instrument_code for contract in self]

        # will contain duplicates, make unique
        unique_list_of_instruments = list(set(list_of_instruments))

        return unique_list_of_instruments

    def contracts_with_price_data_for_instrument_code(self, instrument_code: str):
        list_of_contracts = [
            contract
            for contract in self
            if contract.instrument_code == instrument_code
        ]

        list_of_contracts = listOfFuturesContracts(list_of_contracts)

        return list_of_contracts

    def currently_sampling(self):
        contracts_currently_sampling = [
            contract for contract in self if contract.currently_sampling
        ]

        return listOfFuturesContracts(contracts_currently_sampling)

    def list_of_dates(self) -> list:
        # Return list of contract_date identifiers
        contract_dates = [contract.date_str for contract in self]
        return contract_dates

    def as_dict(self) ->dict:
        contract_dates_keys = self.list_of_dates()
        contract_values = self

        contract_dict = dict([(key, value) for key, value in zip(
            contract_dates_keys, contract_values)])

        return contract_dict

    def difference(self, another_contract_list):

        self_contract_dates = set(self.list_of_dates())
        another_contract_list_dates = set(another_contract_list.list_of_dates())

        list_of_differential_dates =self_contract_dates.difference(another_contract_list_dates)

        list_of_contracts = self._subset_of_list_from_list_of_dates(list_of_differential_dates)

        return list_of_contracts

    def _subset_of_list_from_list_of_dates(self, list_of_dates):
        self_as_dict = self.as_dict()
        list_of_contracts = [
            self_as_dict[contract_date] for contract_date in list_of_dates
        ]

        return listOfFuturesContracts(list_of_contracts)