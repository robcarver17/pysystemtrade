from sysdata.base_data import baseData
from syscore.objects import data_error

from sysobjects.contracts import futuresContract, listOfFuturesContracts
from sysobjects.contract_dates_and_expiries import listOfContractDateStr
from sysobjects.futures_per_contract_prices import futuresContractPrices
from sysobjects.dict_of_futures_per_contract_prices import dictFuturesContractPrices

from syslogdiag.log import logtoscreen

BASE_CLASS_ERROR = "You have used a base class for futures price data; you need to use a class that inherits with a specific data source"

PRICE_FREQ =  ['D', 'H', '5M', 'M', '10S', 'S']

class futuresContractPriceData(baseData):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This would normally be extended further for information from a specific source eg quandl, arctic

    Access via: object.get_prices_for_instrumentCode_and_contractDate('EDOLLAR','201702']
     or object.get_prices_for_contract_object(futuresContract(....))
    """

    def __init__(self, log=logtoscreen("futuresContractPriceData")):
        super().__init__(log=log)

    def __repr__(self):
        return "Individual futures contract price data - DO NOT USE"

    def __getitem__(self, contract_object: futuresContract) -> futuresContractPrices:
        """
        convenience method to get the price, make it look like a dict

        """

        return self.get_prices_for_contract_object(contract_object)

    def keys(self) -> listOfFuturesContracts:
        """
        list of things in this data set (futures contracts, instruments...)

        :returns: list of str

        """
        return self.get_contracts_with_price_data()

    def get_list_of_instrument_codes_with_price_data(self)->list:
        """

        :return: list of str
        """

        list_of_contracts_with_price_data = self.get_contracts_with_price_data()
        unique_list_of_instruments = list_of_contracts_with_price_data.unique_list_of_instrument_codes()

        return unique_list_of_instruments


    def has_data_for_contract(self, contract_object: futuresContract) ->bool:
        list_of_contracts = self.get_contracts_with_price_data()
        if contract_object in list_of_contracts:
            return True
        else:
            return False

    def contracts_with_price_data_for_instrument_code(self, instrument_code: str) -> listOfFuturesContracts:
        """
        Valid contracts

        :param instrument_code: str
        :return: list of contract_date
        """

        list_of_contracts_with_price_data = self.get_contracts_with_price_data()
        list_of_contracts_for_instrument = \
            list_of_contracts_with_price_data.contracts_with_price_data_for_instrument_code(instrument_code)

        return list_of_contracts_for_instrument

    def contract_dates_with_price_data_for_instrument_code(
            self, instrument_code:str) -> listOfContractDateStr:
        """

        :param instrument_code:
        :return: list of str
        """

        list_of_contracts_with_price_data = (
            self.contracts_with_price_data_for_instrument_code(instrument_code)
        )

        contract_dates = [
            str(contract.date_str)
            for contract in list_of_contracts_with_price_data
        ]

        return listOfContractDateStr(contract_dates)


    def get_all_prices_for_instrument(self, instrument_code: str) ->dictFuturesContractPrices:
        """
        Get all the prices for this code, returned as dict

        :param instrument_code: str
        :return: dictFuturesContractPrices
        """

        list_of_contracts = self.contracts_with_price_data_for_instrument_code(instrument_code)
        dict_of_prices = dictFuturesContractPrices(
            [
                (
                    contract.date_str,
                    self.get_prices_for_contract_object(contract),
                )
                for contract in list_of_contracts
            ]
        )

        return dict_of_prices


    def get_prices_for_contract_object(self, contract_object: futuresContract):
        """
        get some prices

        :param contract_object:  futuresContract
        :return: data
        """

        if self.has_data_for_contract(contract_object):
            return self._get_prices_for_contract_object_no_checking(
                contract_object)
        else:
            return futuresContractPrices.create_empty()


    def get_prices_at_frequency_for_contract_object(
            self, contract_object: futuresContract, freq: str="D"):
        """
        get some prices

        :param contract_object:  futuresContract
        :param freq: str; one of D, H, 5M, M, 10S, S
        :return: data
        """
        assert freq in PRICE_FREQ

        if self.has_data_for_contract(contract_object):
            return self._get_prices_at_frequency_for_contract_object_no_checking(
                contract_object, freq=freq)
        else:
            return futuresContractPrices.create_empty()



    def write_prices_for_contract_object(
            self,
            futures_contract_object: futuresContract,
            futures_price_data: futuresContractPrices,
            ignore_duplication=False):
        """
        Write some prices

        :param futures_contract_object:
        :param futures_price_data:
        :param ignore_duplication: bool, to stop us overwriting existing prices
        :return: None
        """

        if self.has_data_for_contract(futures_contract_object):
            if ignore_duplication:
                pass
            else:
                log = futures_contract_object.log(self.log)
                log.warn(
                    "There is already existing data for %s" % futures_contract_object.key)
                return None

        self._write_prices_for_contract_object_no_checking(
            futures_contract_object, futures_price_data
        )


    def update_prices_for_contract(
        self,
        futures_contract_object: futuresContract,
        new_futures_per_contract_prices: futuresContractPrices,
        check_for_spike: bool=True,
    ) -> int:
        """
        Reads existing data, merges with new_futures_prices, writes merged data

        :param new_futures_prices:
        :return: int, number of rows
        """
        new_log = futures_contract_object.log(self.log)

        old_prices = self.get_prices_for_contract_object(
            futures_contract_object)
        merged_prices = old_prices.add_rows_to_existing_data(
            new_futures_per_contract_prices, check_for_spike=check_for_spike
        )

        if merged_prices is data_error:
            new_log.msg(
                "Price has moved too much - will need to manually check - no price updated done")
            return data_error

        rows_added = len(merged_prices) - len(old_prices)

        if rows_added == 0:
            if len(old_prices) == 0:
                new_log.msg("No existing or additional data")
                return 0
            else:
                new_log.msg("No additional data since %s " %
                        str(old_prices.index[-1]))
            return 0

        # We have guaranteed no duplication
        self.write_prices_for_contract_object(
            futures_contract_object, merged_prices, ignore_duplication=True
        )

        new_log.msg("Added %d additional rows of data" % rows_added)

        return rows_added


    def delete_prices_for_contract_object(
        self, futures_contract_object: futuresContract, areyousure=False
    ):
        """

        :param futures_contract_object:
        :return:
        """

        if not areyousure:
            raise Exception(
                "You have to be sure to delete prices_for_contract_object!")

        if self.has_data_for_contract(futures_contract_object):
            self._delete_prices_for_contract_object_with_no_checks_be_careful(
                futures_contract_object
            )
        else:
            log = futures_contract_object.log(self.log)
            log.warn("Tried to delete non existent contract")

    def delete_all_prices_for_instrument_code(
            self, instrument_code:str, areyousure=False):
        # We don't pass areyousure, otherwise if we weren't sure would get
        # multiple exceptions
        if not areyousure:
            raise Exception(
                "You have to be sure to delete_all_prices_for_instrument!")

        all_contracts_to_delete = self.contracts_with_price_data_for_instrument_code(
            instrument_code)
        for contract in all_contracts_to_delete:
            self.delete_prices_for_contract_object(contract, areyousure=True)


    def get_contracts_with_price_data(self) ->listOfFuturesContracts:

        raise NotImplementedError(BASE_CLASS_ERROR)


    def _delete_prices_for_contract_object_with_no_checks_be_careful(
        self, futures_contract_object: futuresContract
    ):
        raise NotImplementedError(BASE_CLASS_ERROR)

    def _write_prices_for_contract_object_no_checking(
        self, futures_contract_object: futuresContract, futures_price_data: futuresContractPrices
    ):

        raise NotImplementedError(BASE_CLASS_ERROR)

    def _get_prices_for_contract_object_no_checking(self, contract_object: futuresContract) -> futuresContractPrices:

        raise NotImplementedError(BASE_CLASS_ERROR)

    def _get_prices_at_frequency_for_contract_object_no_checking(
        self, contract_object: futuresContract, freq: str
    ) -> futuresContractPrices:

        raise NotImplementedError(BASE_CLASS_ERROR)

