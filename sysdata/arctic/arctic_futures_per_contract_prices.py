"""
Read and write data from mongodb for individual futures contracts

"""

from sysdata.arctic.arctic_connection import articConnection
from sysdata.futures.futures_per_contract_prices import futuresContractPriceData, futuresContractPrices

import pandas as pd

CONTRACT_COLLECTION = 'futures_contract_prices'
DEFAULT_DB = 'production'


class arcticFuturesContractPriceData(futuresContractPriceData):
    """
    Class to read / write futures price data to and from arctic
    """

    def __init__(self, database_name= DEFAULT_DB):

        super().__init__()

        self._arctic = articConnection(database_name, collection_name=CONTRACT_COLLECTION)

        self.name = "Data connection for individual futures contracts prices, arctic %s/%s @ %s " % (
            self._arctic.database_name, self._arctic.collection_name, self._arctic.host)

    def __repr__(self):
        return self.name

    def _keyname_given_contract_object(self, futures_contract_object):
        """
        We could do this using the .ident() method of instrument_object, but this way we keep control inside this class

        :param futures_contract_object: futuresContract
        :return: str
        """

        return futures_contract_object.instrument_code + "." + futures_contract_object.date

    def _contract_tuple_given_keyname(self, keyname):
        """
        Extract the two parts of a keyname

        :param keyname: str
        :return: tuple instrument_code, contract_date
        """
        keyname_as_list = keyname.split(".")
        instrument_code, contract_date = tuple(keyname_as_list)

        return instrument_code, contract_date


    def _get_prices_for_contract_object_no_checking(self, futures_contract_object):
        """
        Read back the prices for a given contract object

        :param contract_object:  futuresContract
        :return: data
        """

        ident = self._keyname_given_contract_object(futures_contract_object)
        item = self._arctic.library.read(ident)

        ## What if not found? CHECK

        ## Returns a data frame which should have the right format
        data = item.data

        return futuresContractPrices(data)

    def write_prices_for_contract_object(self, futures_contract_object, futures_price_data):
        """
        Write prices
        CHECK prices are overriden on second write

        :param futures_contract_object: futuresContract
        :param futures_price_data: futuresContractPriceData
        :return: None
        """

        self.log.label(instument_code = futures_contract_object.instrument_code,
                       contract_date = futures_contract_object.contract_date)
        ident = self._keyname_given_contract_object(futures_contract_object)
        self._arctic.library.write(ident, futures_price_data)
        self.log.msg("Wrote %s lines of prices for %s to %s" % (len(futures_price_data), futures_contract_object.ident(), self.name))


    def contracts_with_price_data_for_instrument_code(self, instrument_code):
        """
        Valid contract_dates for a given instrument code

        :param instrument_code: str
        :return: list
        """

        all_keynames = self._all_keynames_in_library()
        all_keynames_as_tuples = [self._contract_tuple_given_keyname(keyname) for keyname in all_keynames]

        all_keynames_for_code = [keyname_tuple[1] for keyname_tuple in all_keynames_as_tuples if keyname_tuple[0]==instrument_code]

        return all_keynames_for_code

    def _all_keynames_in_library(self):
        return self._arctic.library.list_symbols()

    def _delete_prices_for_contract_object_with_no_checks_be_careful(self, futures_contract_object):
        """
        Delete prices for a given contract object without performing any checks

        WILL THIS WORK IF DOESN'T EXIST?
        :param futures_contract_object:
        :return: None
        """
        self.log.label(instument_code = futures_contract_object.instrument_code,
                       contract_date = futures_contract_object.contract_date)

        ident = self._keyname_given_contract_object(futures_contract_object)
        self._arctic.library.delete(ident)
        self.log.msg("Deleted all prices for %s from %s" % (futures_contract_object.ident(), self.name))
