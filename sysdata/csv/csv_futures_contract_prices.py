from dataclasses import  dataclass

from sysdata.futures.futures_per_contract_prices import (
    futuresContractPriceData,
)
from sysobjects.futures_per_contract_prices import futuresContractPrices
from sysobjects.contracts import futuresContract, listOfFuturesContracts
from syslogdiag.log import logtoscreen
from syscore.fileutils import files_with_extension_in_pathname, get_filename_for_package
from syscore.objects import arg_not_supplied
from syscore.pdutils import pd_readcsv, DEFAULT_DATE_FORMAT


@dataclass
class ConfigCsvFuturesPrices:
    input_date_index_name: str = "DATETIME"
    input_date_format: str = DEFAULT_DATE_FORMAT
    input_column_mapping: dict = None
    input_skiprows: int = 0
    input_skipfooter: int = 0


class csvFuturesContractPriceData(futuresContractPriceData):
    """
    Class to read / write individual futures contract price data to and from csv files
# no default datapath supplied as this is not normally used
    """

    def __init__(
        self,
        datapath,
        log=logtoscreen("csvFuturesContractPriceData"),
        config: ConfigCsvFuturesPrices = arg_not_supplied
    ):

        super().__init__(log=log)
        self._datapath = datapath
        if config is arg_not_supplied:
            config = ConfigCsvFuturesPrices()

        self._config = config

    def __repr__(self):
        return "csvFuturesContractPricesData accessing %s" % self._datapath

    @property
    def config(self):
        return self._config

    @property
    def datapath(self):
        return self._datapath

    def _keyname_given_contract_object(self, futures_contract_object: futuresContract) -> str:
        """
        We could do this using the .ident() method of instrument_object, but this way we keep control inside this class

        :param futures_contract_object: futuresContract
        :return: str
        """

        return (
            str(futures_contract_object.instrument)
            + "_"
            + str(futures_contract_object.date_str)
        )

    def _contract_tuple_given_keyname(self, keyname: str) -> tuple:
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
        instrument_code, contract_date = tuple(keyname_as_list)

        return instrument_code, contract_date

    def _get_prices_for_contract_object_no_checking(
            self, futures_contract_object: futuresContract) -> futuresContractPrices:
        """
        Read back the prices for a given contract object

        :param contract_object:  futuresContract
        :return: data
        """
        keyname = self._keyname_given_contract_object(futures_contract_object)
        filename = self._filename_given_key_name(keyname)
        config = self.config

        date_format = config.input_date_format
        date_time_column = config.input_date_index_name
        input_column_mapping = config.input_column_mapping
        skiprows = config.input_skiprows
        skipfooter = config.input_skipfooter

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
            log = futures_contract_object.log(self.log)
            log.warning("Can't find adjusted price file %s" % filename)
            return futuresContractPrices.create_empty()

        instrpricedata = instrpricedata.groupby(level=0).last()

        instrpricedata = futuresContractPrices(instrpricedata)

        return instrpricedata

    def _write_prices_for_contract_object_no_checking(
        self, futures_contract_object: futuresContract, futures_price_data: futuresContractPrices
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
            filename, index_label=self.config.input_date_index_name)

    def _filename_given_key_name(self, keyname: str):
        return get_filename_for_package(self._datapath, "%s.csv" % (keyname))

    def _all_keynames_in_library(self) -> list:
        return files_with_extension_in_pathname(self._datapath, ".csv")

    def _delete_prices_for_contract_object_with_no_checks_be_careful(
        self, futures_contract_object: futuresContract
    ):
        raise NotImplementedError(
            "You can't delete futures prices stored as a csv - Add to overwrite existing data, or delete file manually"
        )

    def _get_contract_tuples_with_price_data(self) -> list:
        """

        :return: list of futures contracts as tuples
        """

        all_keynames = self._all_keynames_in_library()
        list_of_contract_tuples = [self._contract_tuple_given_keyname(
            keyname) for keyname in all_keynames]

        return list_of_contract_tuples

    def get_contracts_with_price_data(self) ->listOfFuturesContracts:
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
