from sysdata.futures.futures_per_contract_prices import (
    futuresContractPriceData,
    futuresContractPrices,
)
from sysdata.futures.contracts import futuresContract
from syslogdiag.log import logtoscreen
from syscore.fileutils import files_with_extension_in_pathname, get_filename_for_package
from syscore.pdutils import pd_readcsv, DEFAULT_DATE_FORMAT

import pandas as pd

# no default datapath supplied as this is not normally used


class csvFuturesContractPriceData(futuresContractPriceData):
    """
    Class to read / write individual futures contract price data to and from csv files
    """

    def __init__(
        self,
        datapath,
        log=logtoscreen("csvFuturesContractPriceData"),
        input_date_index_name="DATETIME",
        input_date_format=DEFAULT_DATE_FORMAT,
        input_column_mapping=None,
        input_skiprows=0,
        input_skipfooter=0,
    ):

        super().__init__(log=log)
        self._datapath = datapath
        self._input_date_format = input_date_format
        self._input_date_time_column = input_date_index_name
        self._input_column_mapping = input_column_mapping
        self._input_skiprows = input_skiprows
        self._input_skipfooter = input_skipfooter

    def __repr__(self):
        return "csvFuturesContractPricesData accessing %s" % self._datapath

    def _keyname_given_contract_object(self, futures_contract_object):
        """
        We could do this using the .ident() method of instrument_object, but this way we keep control inside this class

        :param futures_contract_object: futuresContract
        :return: str
        """

        return (
            str(futures_contract_object.instrument.instrument_code)
            + "_"
            + str(futures_contract_object.contract_date)
        )

    def _contract_tuple_given_keyname(self, keyname):
        """
        Extract the two parts of a keyname

        We keep control of how we represent stuff inside the class

        :param keyname: str
        :return: tuple instrument_code, contract_date
        """
        keyname_as_list = keyname.split("_")

        # It's possible to have GAS_US_20090700.csv, so we only take the second
        if len(keyname_as_list) == 3:
            keyname_as_list = [
                "%s_%s" % (keyname_as_list[0], keyname_as_list[1]),
                keyname_as_list[2],
            ]

        try:
            assert len(keyname_as_list) == 2
        except BaseException:
            self.log.error(
                "Keyname (filename) %s in wrong format should be instrument_contractid" %
                keyname)
            raise
            
        instrument_code, contract_date = tuple(keyname_as_list)

        return instrument_code, contract_date

    def _get_prices_for_contract_object_no_checking(
            self, futures_contract_object):
        """
        Read back the prices for a given contract object

        :param contract_object:  futuresContract
        :return: data
        """
        keyname = self._keyname_given_contract_object(futures_contract_object)
        filename = self._filename_given_key_name(keyname)

        date_format = self._input_date_format
        date_time_column = self._input_date_time_column
        input_column_mapping = self._input_column_mapping
        skiprows = self._input_skiprows
        skipfooter = self._input_skipfooter

        try:
            instrpricedata = pd_readcsv(
                filename,
                date_index_name=date_time_column,
                date_format=date_format,
                input_column_mapping=input_column_mapping,
                skiprows=skiprows,
                skipfooter=skipfooter,
            )
        except OSError:
            self.log.warning("Can't find adjusted price file %s" % filename)
            return futuresContractPrices.create_empty()

        instrpricedata = instrpricedata.groupby(level=0).last()

        instrpricedata = futuresContractPrices(instrpricedata)

        return instrpricedata

    def _write_prices_for_contract_object_no_checking(
        self, futures_contract_object, futures_price_data
    ):
        """
        Write prices
        CHECK prices are overriden on second write

        :param futures_contract_object: futuresContract
        :param futures_price_data: futuresContractPriceData
        :return: None
        """
        keyname = self._keyname_given_contract_object(futures_contract_object)
        filename = self._filename_given_key_name(keyname)
        futures_price_data.to_csv(
            filename, index_label=self._input_date_time_column)

    def _filename_given_key_name(self, keyname):
        return get_filename_for_package(self._datapath, "%s.csv" % (keyname))

    def _all_keynames_in_library(self):
        return files_with_extension_in_pathname(self._datapath, ".csv")

    def _delete_prices_for_contract_object_with_no_checks_be_careful(
        self, futures_contract_object
    ):
        raise NotImplementedError(
            "You can't delete futures prices stored as a csv - Add to overwrite existing or delete file manually"
        )

    def _get_contract_tuples_with_price_data(self):
        """

        :return: list of futures contracts as tuples
        """

        all_keynames = self._all_keynames_in_library()
        list_of_contract_tuples = [self._contract_tuple_given_keyname(
            keyname) for keyname in all_keynames]

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
