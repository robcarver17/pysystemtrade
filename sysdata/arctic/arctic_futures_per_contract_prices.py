"""
Read and write data from mongodb for individual futures contracts

"""

from sysdata.arctic.arctic_connection import articConnection
from sysdata.futures.futures_per_contract_prices import futuresContractPriceData, futuresContractPrices
from sysobjects.contracts import futuresContract
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

        self._arctic = articConnection(CONTRACT_COLLECTION, mongo_db=mongo_db)

        self.name = "simData connection for individual futures contracts prices, arctic %s/%s @ %s " % (
            self._arctic.database_name, self._arctic.collection_name, self._arctic.host)

    def __repr__(self):
        return self.name

    def _keyname_given_contract_object(self, futures_contract_object):
        """
        We could do this using the .ident() method of instrument_object, but this way we keep control inside this class

        :param futures_contract_object: futuresContract
        :return: str
        """

        return futures_contract_object.instrument_code + \
            "." + futures_contract_object.date

    def _contract_tuple_given_keyname(self, keyname):
        """
        Extract the two parts of a keyname

        We keep control of how we represent stuff inside the class

        :param keyname: str
        :return: tuple instrument_code, contract_date
        """
        keyname_as_list = keyname.split(".")
        instrument_code, contract_date = tuple(keyname_as_list)

        return instrument_code, contract_date

    def _get_prices_for_contract_object_no_checking(self,
                                                    futures_contract_object):
        """
        Read back the prices for a given contract object

        :param contract_object:  futuresContract
        :return: data
        """

        ident = self._keyname_given_contract_object(futures_contract_object)
        item = self._arctic.library.read(ident)

        # What if not found? CHECK

        # Returns a data frame which should have the right format
        data = pd.DataFrame(item.data)

        return futuresContractPrices(data)

    def _write_prices_for_contract_object_no_checking(self,
                                                      futures_contract_object,
                                                      futures_price_data):
        """
        Write prices
        CHECK prices are overriden on second write

        :param futures_contract_object: futuresContract
        :param futures_price_data: futuresContractPriceData
        :return: None
        """

        self.log.label(instrument_code=futures_contract_object.instrument_code,
                       contract_date=futures_contract_object.date)
        ident = self._keyname_given_contract_object(futures_contract_object)
        futures_price_data_aspd = pd.DataFrame(futures_price_data)
        self._arctic.library.write(ident, futures_price_data_aspd)
        self.log.msg("Wrote %s lines of prices for %s to %s" %
                     (len(futures_price_data),
                      str(futures_contract_object.key), self.name))

    def _all_keynames_in_library(self):
        return self._arctic.library.list_symbols()

    def _delete_prices_for_contract_object_with_no_checks_be_careful(
            self, futures_contract_object):
        """
        Delete prices for a given contract object without performing any checks

        WILL THIS WORK IF DOESN'T EXIST?
        :param futures_contract_object:
        :return: None
        """
        self.log.label(instrument_code=futures_contract_object.instrument_code,
                       contract_date=futures_contract_object.date)

        ident = self._keyname_given_contract_object(futures_contract_object)
        self._arctic.library.delete(ident)
        self.log.msg("Deleted all prices for %s from %s" %
                     (futures_contract_object.key, self.name))

    def _get_contract_tuples_with_price_data(self):
        """

        :return: list of futures contracts as tuples
        """

        all_keynames = self._all_keynames_in_library()
        list_of_contract_tuples = [
            self._contract_tuple_given_keyname(keyname)
            for keyname in all_keynames
        ]

        return list_of_contract_tuples

    def get_contracts_with_price_data(self):
        """

        :return: list of contracts
        """

        list_of_contract_tuples = self._get_contract_tuples_with_price_data()
        list_of_contracts = [
            futuresContract(contract_tuple[0], contract_tuple[1])
            for contract_tuple in list_of_contract_tuples
        ]

        return list_of_contracts
