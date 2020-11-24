import numpy as np

from syscore.objects import missing_contract, arg_not_supplied, missing_data

from sysobjects.contracts import futuresContract
from sysobjects.dict_of_futures_per_contract_prices import dictFuturesContractPrices
from sysdata.private_config import get_private_then_default_key_value
from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData, futuresContractPrices
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData, futuresMultiplePrices
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData, futuresAdjustedPrices
from sysdata.mongodb.mongo_futures_contracts import mongoFuturesContractData

from sysproduction.data.get_data import dataBlob

from sysobjects.multiple_prices import price_name




class diagPrices(object):
    def __init__(self, data: dataBlob=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list([
            arcticFuturesContractPriceData, arcticFuturesAdjustedPricesData,
         arcticFuturesMultiplePricesData, mongoFuturesContractData]
        )
        self.data = data

    def get_intraday_frequency_for_historical_download(self) -> str:
        intraday_frequency = get_private_then_default_key_value(
            "intraday_frequency")
        return intraday_frequency

    def get_adjusted_prices(self, instrument_code: str) -> futuresAdjustedPrices:
        return self.data.db_futures_adjusted_prices.get_adjusted_prices(
            instrument_code)

    def get_list_of_instruments_in_multiple_prices(self) -> list:
        return self.data.db_futures_multiple_prices.get_list_of_instruments()

    def get_multiple_prices(self, instrument_code: str) -> futuresMultiplePrices:
        return self.data.db_futures_multiple_prices.get_multiple_prices(
            instrument_code)

    def get_prices_for_contract_object(self, contract_object: futuresContract):
        return self.data.db_futures_contract_price.get_prices_for_contract_object(
            contract_object)

    def get_current_contract_prices_for_instrument(self, instrument_code):
        multiple_prices = self.get_multiple_prices(instrument_code)
        return multiple_prices[price_name]

    def get_list_of_instruments_with_contract_prices(self) -> list:
        return self.data.db_futures_contract_price.get_list_of_instrument_codes_with_price_data()

    def contract_dates_with_price_data_for_instrument_code(self, instrument_code: str) -> list:
        return self.data.db_futures_contract_price.contract_dates_with_price_data_for_instrument_code(instrument_code)

    def get_last_matched_prices_for_contract_list(
            self,
            instrument_code: str,
            contract_list: list,
            contracts_to_match=arg_not_supplied) -> list:
        """
        Get a list of matched prices; i.e. from a date when we had both forward and current prices
        If we don't have all the prices, will do the best it can

        :param instrument_code:
        :param contract_list: contract date_str to get prices for
        :param contracts_to_match: (default: contract_list) contracts to match against each other
        :return: list of prices, in same order as contract_list
        """
        if contracts_to_match is arg_not_supplied:
            contracts_to_match = contract_list

        dict_of_prices = self.get_dict_of_prices_for_contract_list(
            instrument_code, contract_list
        )

        last_matched_prices = _price_matching(dict_of_prices, contracts_to_match, contract_list)

        return last_matched_prices

    def get_dict_of_prices_for_contract_list(
            self, instrument_code: str, contract_list: list) -> dictFuturesContractPrices:
        dict_of_prices = {}
        for contract_date_str in contract_list:
            if contract_date_str is missing_contract:
                continue
            # Could blow up here if don't have prices for a contract??
            contract = futuresContract(instrument_code, contract_date_str)
            prices = self.get_prices_for_contract_object(contract)
            dict_of_prices[contract_date_str] = prices

        dict_of_prices = dictFuturesContractPrices(dict_of_prices)

        return dict_of_prices

def _price_matching(dict_of_prices: dictFuturesContractPrices, contracts_to_match: list, contract_list: list):
    dict_of_final_prices = dict_of_prices.final_prices()
    matched_final_prices = dict_of_final_prices.matched_prices(
        contracts_to_match=contracts_to_match
    )

    if matched_final_prices is missing_data:
        # This will happen if there are no matching prices
        # We just return the last row
        matched_final_prices = dict_of_final_prices.joint_data()

    last_matched_prices = list(matched_final_prices.iloc[-1].values)

    # pad with extra nan values
    last_matched_prices = last_matched_prices + [np.nan] * (
        len(contract_list) - len(last_matched_prices)
    )

    return last_matched_prices


class updatePrices(object):
    def __init__(self, data: dataBlob=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list([
            arcticFuturesContractPriceData, arcticFuturesMultiplePricesData,
         mongoFuturesContractData, arcticFuturesAdjustedPricesData]
        )
        self.data = data

    def update_prices_for_contract(
        self, contract_object: futuresContract, new_prices: futuresContractPrices, check_for_spike=True
    ):

        return self.data.db_futures_contract_price.update_prices_for_contract(
            contract_object, new_prices, check_for_spike=check_for_spike
        )

    def add_multiple_prices(
        self, instrument_code: str, updated_multiple_prices: futuresMultiplePrices, ignore_duplication=True
    ):
        return self.data.db_futures_multiple_prices.add_multiple_prices(
            instrument_code, updated_multiple_prices, ignore_duplication=True
        )

    def add_adjusted_prices(
        self, instrument_code: str, updated_adjusted_prices: futuresAdjustedPrices, ignore_duplication=True
    ):
        return self.data.db_futures_adjusted_prices.add_adjusted_prices(
            instrument_code, updated_adjusted_prices, ignore_duplication=True
        )


def get_valid_instrument_code_from_user(
        data: dataBlob=arg_not_supplied, allow_all: bool=False, all_code = "ALL") -> str:
    if data is arg_not_supplied:
        data = dataBlob()
    all_instruments = get_list_of_instruments(data)
    invalid_input = True
    input_prompt = "Instrument code?"
    if allow_all:
        input_prompt = input_prompt + "(Return for ALL)"
    while invalid_input:
        instrument_code = input(input_prompt)

        if allow_all:
            if instrument_code == "" or instrument_code == "ALL":
                return all_code

        if instrument_code in all_instruments:
            break

        print("%s is not in list %s" % (instrument_code, all_instruments))

    return instrument_code

def get_list_of_instruments(data: dataBlob=arg_not_supplied) -> list:
    price_data = diagPrices(data)
    return price_data.get_list_of_instruments_in_multiple_prices()
