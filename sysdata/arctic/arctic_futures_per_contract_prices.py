"""
Read and write data from mongodb for individual futures contracts

"""

from sysdata.arctic.arctic_connection import articConnection
from sysdata.futures.futures_per_contract_prices import futuresContractPriceData, listOfFuturesContracts
from sysobjects.futures_per_contract_prices import futuresContractPrices
from sysobjects.contracts import futuresContract, get_code_and_id_from_contract_key
from syslogdiag.log import logtoscreen

import pandas as pd

CONTRACT_COLLECTION = 'futures_contract_prices'


class arcticFuturesContractPriceData(futuresContractPriceData):
    """
    Class to read / write futures price data to and from arctic
    """

    def __init__(self,
                 mongo_db=None,
                 log=logtoscreen("arcticFuturesContractPriceData")):

        super().__init__(log=log)

        self._arctic_connection = articConnection(CONTRACT_COLLECTION, mongo_db=mongo_db)

    def __repr__(self):
        return "simData connection for individual futures contracts prices, arctic %s/%s @ %s " % (
            self._arctic_connection.database_name, self._arctic_connection.collection_name, self._arctic_connection.host)

    @property
    def arctic_connection(self):
        return self._arctic_connection


    def _get_prices_for_contract_object_no_checking(self,
                                                    futures_contract_object: futuresContract) -> futuresContractPrices:
        """
        Read back the prices for a given contract object

        :param contract_object:  futuresContract
        :return: data
        """

        ident = from_contract_to_key(futures_contract_object)

        # Returns a data frame which should have the right format
        data = self.arctic_connection.read(ident)

        return futuresContractPrices(data)

    def _write_prices_for_contract_object_no_checking(self,
                                                      futures_contract_object: futuresContract,
                                                      futures_price_data: futuresContractPrices):
        """
        Write prices
        CHECK prices are overriden on second write

        :param futures_contract_object: futuresContract
        :param futures_price_data: futuresContractPriceData
        :return: None
        """

        log = futures_contract_object.log(self.log)
        ident = from_contract_to_key(futures_contract_object)
        futures_price_data_as_pd = pd.DataFrame(futures_price_data)

        self.arctic_connection.write(ident, futures_price_data_as_pd)

        log.msg("Wrote %s lines of prices for %s to %s" %
                     (len(futures_price_data),
                      str(futures_contract_object.key), str(self)))

    def get_contracts_with_price_data(self) -> listOfFuturesContracts:
        """

        :return: list of contracts
        """

        list_of_contract_tuples = self._get_contract_tuples_with_price_data()
        list_of_contracts = [
            futuresContract(contract_tuple[0], contract_tuple[1])
            for contract_tuple in list_of_contract_tuples
        ]

        list_of_contracts = listOfFuturesContracts(list_of_contracts)

        return list_of_contracts

    def _get_contract_tuples_with_price_data(self) -> list:
        """

        :return: list of futures contracts as tuples
        """

        all_keynames = self._all_keynames_in_library()
        list_of_contract_tuples = [
            from_key_to_tuple(keyname)
            for keyname in all_keynames
        ]

        return list_of_contract_tuples

    def _all_keynames_in_library(self) -> list:
        return self.arctic_connection.get_keynames()

    def _delete_prices_for_contract_object_with_no_checks_be_careful(
            self, futures_contract_object: futuresContract):
        """
        Delete prices for a given contract object without performing any checks

        WILL THIS WORK IF DOESN'T EXIST?
        :param futures_contract_object:
        :return: None
        """
        log = futures_contract_object.log(self.log)

        ident = from_contract_to_key(futures_contract_object)
        self.arctic_connection.delete(ident)
        log.msg("Deleted all prices for %s from %s" %
                     (futures_contract_object.key, str(self)))


def from_key_to_tuple(keyname):
    return keyname.split(".")

def from_contract_to_key(contract: futuresContract):
    return from_tuple_to_key([contract.instrument_code, contract.date_str])

def from_tuple_to_key(keytuple):
    return keytuple[0]+"."+keytuple[1]