import datetime

from syscore.objects import missing_contract, arg_not_supplied

from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.mongodb.mongo_roll_data import mongoRollParametersData
from sysdata.mongodb.mongo_futures_contracts import mongoFuturesContractData

from sysobjects.contract_dates_and_expiries import contractDate
from sysobjects.rolls import contractDateWithRollParameters
from sysobjects.dict_of_named_futures_per_contract_prices import setOfNamedContracts
from sysobjects.contracts import futuresContract

from sysproduction.data.prices import get_valid_instrument_code_from_user, diagPrices
from sysproduction.data.get_data import dataBlob

missing_expiry = datetime.datetime(1900, 1, 1)


class diagContracts(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list([
            arcticFuturesContractPriceData, mongoRollParametersData,
                            arcticFuturesMultiplePricesData, mongoFuturesContractData]
        )
        self.data = data

    def is_contract_in_data(self, instrument_code, contract_date):
        return self.data.db_futures_contract.is_contract_in_data(
            instrument_code, contract_date
        )

    def get_all_contract_objects_for_instrument_code(self, instrument_code):
        return (
            self.data.db_futures_contract.get_all_contract_objects_for_instrument_code(
                instrument_code
            )
        )


    def get_labelled_list_of_contracts_from_contract_list(self, contract_list):
        instrument_code = contract_list[0].instrument_code
        list_of_dates = contract_list.list_of_dates()

        labelled_list = self.get_labelled_list_of_contracts_from_contract_date_list(instrument_code, list_of_dates)

        return labelled_list

    def get_labelled_list_of_contracts_from_contract_date_list(self, instrument_code, list_of_dates):
        current_contracts = self.get_current_contract_dict(instrument_code)

        labelled_list = label_up_contracts(list_of_dates, current_contracts)

        return labelled_list


    def get_all_sampled_contracts(self, instrument_code):
        all_contracts = self.get_all_contract_objects_for_instrument_code(instrument_code)
        sampled_contracts = all_contracts.currently_sampling()

        return sampled_contracts

    def get_labelled_list_of_relevant_contracts(self, instrument_code):

        current_contracts = self.get_current_contract_dict(instrument_code)

        contract_date_list = self.extend_current_contracts(
            instrument_code, current_contracts
        )

        labelled_contracts = label_up_contracts(
            contract_date_list, current_contracts)

        ans_as_dict = dict(
            contracts=contract_date_list,
            labels=labelled_contracts,
            current_contracts=current_contracts,
        )

        return ans_as_dict

    def get_current_contract_dict(self, instrument_code) ->setOfNamedContracts:
        multiple_prices = self.data.db_futures_multiple_prices.get_multiple_prices(
            instrument_code)
        current_contracts = multiple_prices.current_contract_dict()

        return current_contracts

    def extend_current_contracts(self, instrument_code, current_contracts):

        price_contract_date = current_contracts.price
        forward_contract_date = current_contracts.forward
        carry_contract_date = current_contracts.carry

        roll_parameters = self.get_roll_parameters(instrument_code)

        price_contract = contractDateWithRollParameters(
            contractDate(price_contract_date), roll_parameters
        )
        forward_contract = contractDateWithRollParameters(
            contractDate(forward_contract_date), roll_parameters
        )
        carry_contract = contractDateWithRollParameters(
            contractDate(carry_contract_date), roll_parameters
        )

        preceeding_price_contract_date = price_contract.previous_priced_contract()
        preceeding_forward_contract_date = forward_contract.previous_priced_contract()
        subsequent_forward_contract_date = forward_contract.next_held_contract()

        # Could be up to 6 contracts
        # HOW TO PAD THESE ?
        all_contracts = [
            price_contract,
            forward_contract,
            preceeding_forward_contract_date,
            preceeding_price_contract_date,
            subsequent_forward_contract_date,
            carry_contract,
        ]

        all_contracts_dates = [
            contract.date_str for contract in all_contracts]
        unique_all_contract_dates = sorted(set(all_contracts_dates))
        unique_all_contract_dates = unique_all_contract_dates + \
            [missing_contract] * (6 - len(unique_all_contract_dates))

        return unique_all_contract_dates

    def get_roll_parameters(self, instrument_code):
        roll_parameters = self.data.db_roll_parameters.get_roll_parameters(
            instrument_code
        )
        return roll_parameters


    def get_contract_object(self, instrument_code, contract_id):

        contract_object = self.data.db_futures_contract.get_contract_object(
            instrument_code, contract_id
        )

        return contract_object

    def get_actual_expiry(self, instrument_code, contract_id):
        contract_object = self.get_contract_object(
            instrument_code, contract_id)

        expiry_date = contract_object.expiry_date

        return expiry_date

    def get_priced_contract_id(self, instrument_code):
        contract_dict = self.get_current_contract_dict(instrument_code)
        price_contract = contract_dict.price
        return price_contract

    def get_carry_contract_id(self, instrument_code):
        contract_dict = self.get_current_contract_dict(instrument_code)
        carry_contract = contract_dict.carry
        return carry_contract

    def get_forward_contract_id(self, instrument_code):
        contract_dict = self.get_current_contract_dict(instrument_code)
        carry_contract = contract_dict.forward
        return carry_contract

    def get_priced_expiry(self, instrument_code):
        contract_id = self.get_priced_contract_id(instrument_code)
        return self.get_actual_expiry(instrument_code, contract_id)

    def get_carry_expiry(self, instrument_code):
        contract_id = self.get_carry_contract_id(instrument_code)
        return self.get_actual_expiry(instrument_code, contract_id)

    def when_to_roll_priced_contract(self, instrument_code):
        priced_contract_id = self.get_priced_contract_id(instrument_code)

        contract_date_with_roll_parameters = (
            self.get_contract_date_object_with_roll_parameters(
                instrument_code, priced_contract_id
            )
        )

        return contract_date_with_roll_parameters.desired_roll_date

    def get_contract_date_object_with_roll_parameters(
        self, instrument_code:str, contract_date_str:str
    ) -> contractDateWithRollParameters:

        roll_parameters = self.get_roll_parameters(instrument_code)
        contract_date = self.get_contract_date_object(instrument_code, contract_date_str)

        contract_date_with_roll_parameters = contractDateWithRollParameters(
            contract_date, roll_parameters
        )

        return contract_date_with_roll_parameters

    def get_contract_date_object(self, instrument_code:str, contract_date_str: str) -> contractDate:
        contract = self.get_contract_object(instrument_code, contract_date_str)
        contract_date = contract.contract_date

        return contract_date

def get_valid_contract_object_from_user(data, instrument_code=None, include_priced_contracts = False):
    instrument_code , contract_date_str = get_valid_instrument_code_and_contractid_from_user(data,
                                                                                             instrument_code = instrument_code,
                                                                                             include_priced_contracts = include_priced_contracts)

    return futuresContract(instrument_code, contract_date_str)

def get_valid_instrument_code_and_contractid_from_user(
        data, instrument_code=None, include_priced_contracts = False):
    diag_contracts = diagContracts(data)
    diag_prices = diagPrices(data)

    invalid_input = True
    while invalid_input:
        if instrument_code is None:
            instrument_code = get_valid_instrument_code_from_user(data)

        if include_priced_contracts:
            dates_to_choose_from = diag_prices.contract_dates_with_price_data_for_instrument_code(instrument_code)
        else:
            contract_list = diag_contracts.get_all_contract_objects_for_instrument_code(
                instrument_code)
            dates_to_choose_from = contract_list.list_of_dates()

        dates_to_display = diag_contracts.get_labelled_list_of_contracts_from_contract_date_list(instrument_code,
                                                                                                 dates_to_choose_from)

        if len(dates_to_choose_from) == 0:
            print(
                "%s is not an instrument with contract data" %
                instrument_code)
            instrument_code = None
            continue
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


def label_up_contracts(contract_date_list, current_contracts):
    """
    Labels some contracts

    :param contract_date_list: list of str, yyyymmdd
    :return: list of yyymm, with _p (price) _f (forward) _c (carry) suffixes
    """
    price_contract_date = current_contracts["PRICE"]
    forward_contract_date = current_contracts["FORWARD"]
    carry_contract_date = current_contracts["CARRY"]

    contract_names = []
    for contract in contract_date_list:
        if contract is missing_contract:
            suffix = ""
            contract_names.append("")
            continue

        if contract == price_contract_date:
            suffix = "p"
        elif contract == forward_contract_date:
            suffix = "f"
        elif contract == carry_contract_date:
            suffix = "c"
        else:
            suffix = ""
        contract_names.append("%s%s" % (contract, suffix))

    return contract_names


class updateContracts(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoFuturesContractData)
        self.data = data

    def add_contract_data(self, contract, ignore_duplication=False):
        return self.data.db_futures_contract.add_contract_data(
            contract, ignore_duplication=ignore_duplication
        )
