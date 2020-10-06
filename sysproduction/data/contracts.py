import datetime

from sysdata.futures.rolls import contractDateWithRollParameters
from sysdata.futures.contracts import futuresContract
from sysproduction.data.prices import get_valid_instrument_code_from_user
from sysproduction.data.get_data import dataBlob
from syscore.objects import missing_contract, arg_not_supplied

missing_expiry = datetime.datetime(1900, 1, 1)


class diagContracts(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list(
            "arcticFuturesContractPriceData mongoRollParametersData \
                            arcticFuturesMultiplePricesData mongoFuturesContractData"
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

    def get_current_contract_dict(self, instrument_code):
        multiple_prices = self.data.db_futures_multiple_prices.get_multiple_prices(
            instrument_code)
        current_contracts = multiple_prices.current_contract_dict()

        return current_contracts

    def extend_current_contracts(self, instrument_code, current_contracts):

        price_contract_date = current_contracts["PRICE"]
        forward_contract_date = current_contracts["FORWARD"]
        carry_contract_date = current_contracts["CARRY"]

        roll_parameters = self.get_roll_parameters(instrument_code)

        price_contract = contractDateWithRollParameters(
            roll_parameters, price_contract_date
        )
        forward_contract = contractDateWithRollParameters(
            roll_parameters, forward_contract_date
        )
        carry_contract = contractDateWithRollParameters(
            roll_parameters, carry_contract_date
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
            contract.contract_date for contract in all_contracts]
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
        contract_object = self.get_contract_data(instrument_code, contract_id)
        if contract_object.empty():
            contract_object = futuresContract(instrument_code, contract_id)

        return contract_object

    def get_contract_data(self, instrument_code, contract_id):
        contract_object = self.data.db_futures_contract.get_contract_data(
            instrument_code, contract_id
        )

        return contract_object

    def get_actual_expiry(self, instrument_code, contract_id):
        contract_object = self.get_contract_object(
            instrument_code, contract_id)
        if contract_object.empty():
            return missing_expiry

        expiry_date = contract_object.expiry_date

        return expiry_date

    def get_priced_contract_id(self, instrument_code):
        contract_dict = self.get_current_contract_dict(instrument_code)
        price_contract = contract_dict["PRICE"]
        return price_contract

    def get_carry_contract_id(self, instrument_code):
        contract_dict = self.get_current_contract_dict(instrument_code)
        carry_contract = contract_dict["CARRY"]
        return carry_contract

    def get_forward_contract_id(self, instrument_code):
        contract_dict = self.get_current_contract_dict(instrument_code)
        carry_contract = contract_dict["FORWARD"]
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

        return contract_date_with_roll_parameters.want_to_roll()

    def get_contract_date_object_with_roll_parameters(
        self, instrument_code, contract_date_id
    ):
        roll_parameters = self.get_roll_parameters(instrument_code)

        contract_date_with_roll_parameters = contractDateWithRollParameters(
            roll_parameters, contract_date_id
        )

        return contract_date_with_roll_parameters


def get_valid_instrument_code_and_contractid_from_user(
        data, instrument_code=None):
    diag_contracts = diagContracts(data)
    invalid_input = True
    while invalid_input:
        if instrument_code is None:
            instrument_code = get_valid_instrument_code_from_user(data)
        all_contracts = diag_contracts.get_all_contract_objects_for_instrument_code(
            instrument_code)
        sampled_contract = all_contracts.currently_sampling()
        sampled_dates = sampled_contract.list_of_dates()
        all_dates = all_contracts.list_of_dates()
        if len(all_dates) == 0:
            print(
                "%s is not an instrument with contract data" %
                instrument_code)
            instrument_code = None
            continue
        print("Currently sampled contract dates %s" % str(sampled_dates))
        contract_date = input("Contract date? [yyyymm or yyyymmdd]")
        if len(contract_date) == 6:
            contract_date = contract_date + "00"
        if contract_date in all_dates:
            break
        else:
            print("%s is not in list %s" % (contract_date, all_dates))
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

        data.add_class_list("mongoFuturesContractData")
        self.data = data

    def add_contract_data(self, contract, ignore_duplication=False):
        return self.data.db_futures_contract.add_contract_data(
            contract, ignore_duplication=ignore_duplication
        )
