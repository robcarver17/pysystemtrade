from sysdata.futures.futures_per_contract_prices import dictFuturesContractPrices
from sysproduction.data.get_data import dataBlob
from syscore.objects import missing_contract, arg_not_supplied, missing_data
import numpy as np

class diagPrices(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("arcticFuturesContractPriceData")
        self.data = data

    def get_last_matched_prices_for_contract_list(self, instrument_code, contract_list,
                                                  contracts_to_match = arg_not_supplied):
        """
        Get a list of matched prices; i.e. from a date when we had both forward and current prices
        If we don't have all the prices, will do the best it can

        :param instrument_code:
        :param contract_list: contracts to get prices for
        :param contracts_to_match: (default: contract_list) contracts to match against each other
        :return: list of prices, in same order as contract_list
        """
        if contracts_to_match is arg_not_supplied:
            contracts_to_match = contract_list

        dict_of_prices = self.get_dict_of_prices_for_contract_list(instrument_code, contract_list)
        dict_of_final_prices = dict_of_prices.final_prices()
        matched_final_prices =  dict_of_final_prices.matched_prices(contracts_to_match=contracts_to_match)

        if matched_final_prices is missing_data:
            ## This will happen if there are no matching prices
            ## We just return the last row
            matched_final_prices = dict_of_final_prices.joint_data()

        last_matched_prices = list(matched_final_prices.iloc[-1].values)

        # pad
        last_matched_prices = last_matched_prices + [np.nan] * (len(contract_list) - len(last_matched_prices))

        return last_matched_prices


    def get_dict_of_prices_for_contract_list(self, instrument_code, contract_list):
        dict_of_prices = {}
        for contract_date in contract_list:
            if contract_date is missing_contract:
                continue
            ## Could blow up here if don't have prices for a contract??
            prices = self.data.\
                arctic_futures_contract_price.get_prices_for_instrument_code_and_contract_date(instrument_code,
                                                                                                     contract_date)
            dict_of_prices[contract_date] = prices

        dict_of_prices = dictFuturesContractPrices(dict_of_prices)

        return dict_of_prices
