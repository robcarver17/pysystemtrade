from sysdata.futures.futures_per_contract_prices import dictFuturesContractPrices
from syscore.objects import missing_contract
import numpy as np

class diagPrices(object):
    def __init__(self, data):
        # Check data has the right elements to do this

        data.add_class_list("arcticFuturesContractPriceData")
        self.data = data

    def get_last_matched_prices_for_contract_list(self, instrument_code, contract_list):
        """
        Get a list of matched prices; i.e.

        :param instrument_code:
        :param contract_list:
        :return:
        """
        dict_of_prices = self.get_dict_of_prices_for_contract_list(instrument_code, contract_list)
        dict_of_final_prices = dict_of_prices.final_prices()
        matched_final_prices =  dict_of_final_prices.matched_prices()

        last_matched_prices = list(matched_final_prices.iloc[-1].values)

        # pad
        last_matched_prices = last_matched_prices + [np.nan] * (len(contract_list) - len(last_matched_prices))

        return last_matched_prices

    def get_last_matched_prices_for_contract_list(self, instrument_code, contract_list):
        """
        Get a list of matched prices; i.e.

        :param instrument_code:
        :param contract_list:
        :return:
        """
        dict_of_prices = self.get_dict_of_prices_for_contract_list(instrument_code, contract_list)
        dict_of_final_prices = dict_of_prices.final_prices()
        matched_final_prices =  dict_of_final_prices.matched_prices()

        last_matched_prices = list(matched_final_prices.iloc[-1].values)

        # pad
        last_matched_prices = last_matched_prices + [np.nan] * (len(contract_list) - len(last_matched_prices))

        return last_matched_prices


    def get_dict_of_prices_for_contract_list(self, instrument_code, contract_list):
        dict_of_prices = {}
        for contract_date in contract_list:
            if contract_date is missing_contract:
                continue
            prices = self.data.\
                arctic_futures_contract_price.get_prices_for_instrument_code_and_contract_date(instrument_code,
                                                                                                     contract_date)
            dict_of_prices[contract_date] = prices

        dict_of_prices = dictFuturesContractPrices(dict_of_prices)

        return dict_of_prices
