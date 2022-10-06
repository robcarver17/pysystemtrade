import datetime

from syscore.objects import missing_contract, missing_data

from sysdata.arctic.arctic_futures_per_contract_prices import (
    arcticFuturesContractPriceData,
)
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData
from sysdata.mongodb.mongo_futures_contracts import mongoFuturesContractData

from sysdata.futures.contracts import futuresContractData
from sysdata.futures.multiple_prices import futuresMultiplePricesData
from sysdata.futures.rolls_parameters import rollParametersData

from sysobjects.contract_dates_and_expiries import (
    contractDate,
    expiryDate,
    listOfContractDateStr,
)
from sysobjects.rolls import contractDateWithRollParameters, rollParameters
from sysobjects.dict_of_named_futures_per_contract_prices import setOfNamedContracts
from sysobjects.contracts import futuresContract, listOfFuturesContracts

from sysproduction.data.prices import get_valid_instrument_code_from_user, diagPrices
from sysproduction.data.generic_production_data import productionDataLayerGeneric
from sysdata.data_blob import dataBlob

missing_expiry = datetime.datetime(1900, 1, 1)


class dataContracts(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_list(
            [
                arcticFuturesContractPriceData,
                mongoRollParametersData,
                arcticFuturesMultiplePricesData,
                mongoFuturesContractData,
            ]
        )

        return data

    @property
    def db_contract_data(self) -> futuresContractData:
        return self.data.db_futures_contract

    @property
    def db_multiple_prices_data(self) -> futuresMultiplePricesData:
        return self.data.db_futures_multiple_prices

    @property
    def db_roll_parameters(self) -> rollParametersData:
        return self.data.db_roll_parameters

    def days_until_roll(self, instrument_code) -> int:
        when_to_roll = self.when_to_roll_priced_contract(instrument_code)
        now = datetime.datetime.now()
        when_to_roll_days = (when_to_roll - now).days

        return when_to_roll_days

    def days_until_price_expiry(self, instrument_code: str) -> int:
        price_expiry = self.get_priced_expiry(instrument_code)
        now = datetime.datetime.now()
        price_expiry_days = (price_expiry - now).days

        return price_expiry_days

    def days_until_carry_expiry(self, instrument_code: str) -> int:
        carry_expiry = self.get_carry_expiry(instrument_code)
        now = datetime.datetime.now()
        carry_expiry_days = (carry_expiry - now).days

        return carry_expiry_days

    def is_contract_in_data(self, contract: futuresContract):
        instrument_code = contract.instrument_code
        contract_date_str = contract.date_str

        return self.db_contract_data.is_contract_in_data(
            instrument_code=instrument_code, contract_date_str=contract_date_str
        )

    def mark_contract_as_sampling(self, contract: futuresContract):
        contract_to_modify = self.get_contract_from_db(contract)
        if contract_to_modify is missing_data:
            raise Exception("Can't mark non existent contract as sampling")
        # Mark it as sampling
        contract_to_modify.sampling_on()

        self.add_contract_data(contract_to_modify, ignore_duplication=True)

    def mark_contract_as_not_sampling(self, contract: futuresContract):
        contract_to_modify = self.get_contract_from_db(contract)
        if contract_to_modify is missing_data:
            raise Exception("Can't mark non existent contract as sampling")

        # Mark it as sampling
        contract_to_modify.sampling_off()

        self.add_contract_data(contract_to_modify, ignore_duplication=True)

    def update_expiry_date(
        self, contract: futuresContract, new_expiry_date: expiryDate
    ):

        contract_to_modify = self.get_contract_from_db(contract)
        if contract_to_modify is missing_data:
            raise Exception("Can't update expiry date for non existent contract")

        contract_to_modify.update_single_expiry_date(new_expiry_date)

        self.add_contract_data(contract_to_modify, ignore_duplication=True)

    def add_contract_data(
        self, contract: futuresContract, ignore_duplication: bool = False
    ):
        return self.db_contract_data.add_contract_data(
            contract, ignore_duplication=ignore_duplication
        )

    def get_all_contract_objects_for_instrument_code(
        self, instrument_code: str
    ) -> listOfFuturesContracts:
        list_of_contracts = (
            self.db_contract_data.get_all_contract_objects_for_instrument_code(
                instrument_code
            )
        )

        return list_of_contracts

    def get_labelled_list_of_contracts_from_contract_date_list(
        self, instrument_code: str, list_of_dates: listOfContractDateStr
    ) -> list:
        current_contracts = self.get_current_contract_dict(instrument_code)
        if current_contracts is missing_data:
            return list_of_dates

        labelled_list = label_up_contracts_with_date_list(
            list_of_dates, current_contracts
        )

        return labelled_list

    def get_all_sampled_contracts(self, instrument_code: str) -> listOfFuturesContracts:
        all_contracts = self.get_all_contract_objects_for_instrument_code(
            instrument_code
        )
        sampled_contracts = all_contracts.currently_sampling()

        return sampled_contracts

    def get_labelled_dict_of_current_contracts(self, instrument_code: str) -> dict:

        current_contracts = self.get_current_contract_dict(instrument_code)

        list_of_date_str, labelled_contracts = label_up_current_contracts(
            current_contracts
        )

        ans_as_dict = dict(contracts=list_of_date_str, labels=labelled_contracts)

        return ans_as_dict

    def get_current_contract_dict(self, instrument_code) -> setOfNamedContracts:
        multiple_prices = self.db_multiple_prices_data.get_multiple_prices(
            instrument_code
        )
        current_contracts = multiple_prices.current_contract_dict()

        return current_contracts

    def update_roll_parameters(self, instrument_code: str,
                               roll_parameters: rollParameters):

        self.db_roll_parameters.add_roll_parameters(instrument_code=instrument_code,
                                                    roll_parameters=roll_parameters,
                                                    ignore_duplication=True)

    def get_roll_parameters(self, instrument_code: str) -> rollParameters:
        roll_parameters = self.db_roll_parameters.get_roll_parameters(instrument_code)
        return roll_parameters

    def get_contract_from_db(self, contract: futuresContract) -> futuresContract:
        db_contract = self.get_contract_from_db_given_code_and_id(
            instrument_code=contract.instrument_code, contract_id=contract.date_str
        )

        return db_contract

    def get_contract_from_db_given_code_and_id(
        self, instrument_code: str, contract_id: str
    ) -> futuresContract:

        contract_object = self.db_contract_data.get_contract_object(
            instrument_code=instrument_code, contract_id=contract_id
        )

        return contract_object

    def _get_actual_expiry(self, instrument_code: str, contract_id: str) -> expiryDate:
        contract_object = self.get_contract_from_db_given_code_and_id(
            instrument_code, contract_id
        )

        expiry_date = contract_object.expiry_date

        return expiry_date

    def get_priced_contract_id(self, instrument_code: str) -> str:
        contract_dict = self.get_current_contract_dict(instrument_code)
        price_contract = contract_dict.price

        return price_contract

    def _get_carry_contract_id(self, instrument_code: str) -> str:
        contract_dict = self.get_current_contract_dict(instrument_code)
        carry_contract = contract_dict.carry
        return carry_contract

    def get_forward_contract_id(self, instrument_code: str) -> str:
        contract_dict = self.get_current_contract_dict(instrument_code)
        carry_contract = contract_dict.forward
        return carry_contract

    def get_priced_expiry(self, instrument_code: str) -> expiryDate:
        contract_id = self.get_priced_contract_id(instrument_code)
        return self._get_actual_expiry(instrument_code, contract_id)

    def get_carry_expiry(self, instrument_code: str) -> expiryDate:
        contract_id = self._get_carry_contract_id(instrument_code)
        return self._get_actual_expiry(instrument_code, contract_id)

    def when_to_roll_priced_contract(self, instrument_code: str) -> datetime.datetime:
        priced_contract_id = self.get_priced_contract_id(instrument_code)

        contract_date_with_roll_parameters = (
            self.get_contract_date_object_with_roll_parameters(
                instrument_code, priced_contract_id
            )
        )

        return contract_date_with_roll_parameters.desired_roll_date

    def get_contract_date_object_with_roll_parameters(
        self, instrument_code: str, contract_date_str: str
    ) -> contractDateWithRollParameters:

        roll_parameters = self.get_roll_parameters(instrument_code)
        contract_date = self._get_contract_date_object(
            instrument_code, contract_date_str
        )

        contract_date_with_roll_parameters = contractDateWithRollParameters(
            contract_date, roll_parameters
        )

        return contract_date_with_roll_parameters

    def _get_contract_date_object(
        self, instrument_code: str, contract_date_str: str
    ) -> contractDate:
        contract = self.get_contract_from_db_given_code_and_id(
            instrument_code, contract_date_str
        )
        contract_date = contract.contract_date

        return contract_date

    def delete_all_contracts_for_instrument(self, instrument_code: str, are_you_sure: bool = False):
        self.db_contract_data.delete_all_contracts_for_instrument(instrument_code, areyoureallysure=are_you_sure)

def get_valid_contract_object_from_user(
    data: dataBlob,
    instrument_code: str = None,
    only_include_priced_contracts: bool = False,
) -> futuresContract:

    (
        instrument_code,
        contract_date_str,
    ) = get_valid_instrument_code_and_contractid_from_user(
        data,
        instrument_code=instrument_code,
        only_include_priced_contracts=only_include_priced_contracts,
    )
    contract = futuresContract(instrument_code, contract_date_str)
    return contract


def get_valid_instrument_code_and_contractid_from_user(
    data: dataBlob,
    instrument_code: str = None,
    only_include_priced_contracts: bool = False,
) -> (str, str):

    diag_contracts = dataContracts(data)

    invalid_input = True
    while invalid_input:
        if instrument_code is None:
            instrument_code = get_valid_instrument_code_from_user(data, source="single")

        dates_to_choose_from = get_dates_to_choose_from(
            data=data,
            instrument_code=instrument_code,
            only_priced_contracts=only_include_priced_contracts,
        )

        if len(dates_to_choose_from) == 0:
            print("%s is not an instrument with contract data" % instrument_code)
            instrument_code = None
            continue

        dates_to_display = (
            diag_contracts.get_labelled_list_of_contracts_from_contract_date_list(
                instrument_code, dates_to_choose_from
            )
        )

        print("Available contract dates %s" % str(dates_to_display))
        print("p = currently priced, c=current carry, f= current forward")
        contract_date = input("Contract date? [yyyymm or yyyymmdd] (ignore suffixes)")
        if len(contract_date) == 6:
            contract_date = contract_date + "00"
        if contract_date in dates_to_choose_from:
            break
        else:
            print("%s is not in list %s" % (contract_date, dates_to_choose_from))
            continue  # not required

    return instrument_code, contract_date


def get_dates_to_choose_from(
    data: dataBlob, instrument_code: str, only_priced_contracts: bool = False
) -> listOfContractDateStr:

    diag_contracts = dataContracts(data)
    diag_prices = diagPrices(data)
    if only_priced_contracts:
        dates_to_choose_from = (
            diag_prices.contract_dates_with_price_data_for_instrument_code(
                instrument_code
            )
        )
    else:
        contract_list = diag_contracts.get_all_contract_objects_for_instrument_code(
            instrument_code
        )
        dates_to_choose_from = contract_list.list_of_dates()

    dates_to_choose_from = listOfContractDateStr(dates_to_choose_from)
    dates_to_choose_from = dates_to_choose_from.sorted_date_str()

    return dates_to_choose_from


PRICE_SUFFIX = "p"
CARRY_SUFFIX = "c"
FORWARD_SUFFIX = "f"
EMPTY_SUFFIX = ""


def label_up_contracts_with_date_list(
    contract_date_list: listOfContractDateStr, current_contracts: setOfNamedContracts
) -> list:
    """
    Labels some contracts

    :param contract_date_list: list of str, yyyymmdd
    :return: list of yyymm, with _p (price) _f (forward) _c (carry) suffixes
    """
    price_contract_date = current_contracts.price
    forward_contract_date = current_contracts.forward
    carry_contract_date = current_contracts.carry

    contract_names = []
    for contract in contract_date_list:
        if contract is missing_contract:
            contract_names.append("")
            continue

        if contract == price_contract_date:
            suffix = PRICE_SUFFIX
        elif contract == forward_contract_date:
            suffix = FORWARD_SUFFIX
        elif contract == carry_contract_date:
            suffix = CARRY_SUFFIX
        else:
            suffix = EMPTY_SUFFIX

        contract_names.append("%s%s" % (contract, suffix))

    return contract_names


def label_up_current_contracts(
    current_contracts: setOfNamedContracts,
) -> (listOfContractDateStr, list):
    """
    Labels current contracts only

    """
    price_contract_date = current_contracts.price
    forward_contract_date = current_contracts.forward
    carry_contract_date = current_contracts.carry

    labelled_price_contract = "%s%s" % (price_contract_date, PRICE_SUFFIX)
    labelled_forward_contract = "%s%s" % (forward_contract_date, FORWARD_SUFFIX)
    labelled_carry_contract = "%s%s" % (carry_contract_date, CARRY_SUFFIX)
    contract_names = [
        labelled_carry_contract,
        labelled_price_contract,
        labelled_forward_contract,
    ]
    contract_date_list = [
        carry_contract_date,
        price_contract_date,
        forward_contract_date,
    ]
    contract_date_list = listOfContractDateStr(contract_date_list)

    return contract_date_list, contract_names
