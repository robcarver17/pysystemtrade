from sysdata.futures.futures_per_contract_prices import (
    futuresContractPriceData,
)
from sysobjects.futures_per_contract_prices import futuresContractPrices
from sysobjects.contracts import futuresContract, listOfFuturesContracts
from syslogdiag.log_to_screen import logtoscreen
from syscore.objects import arg_not_supplied, missing_instrument
from syscore.dateutils import DAILY_PRICE_FREQ, Frequency
import datetime
from sysdata.csv.parametric_csv_database import parametricCsvDatabase, ConfigCsvFuturesPrices


class csvFuturesContractPriceData(futuresContractPriceData):
    """
    Class to read / write individual futures contract price data to and from csv files
    """

    def __init__(
        self,
        datapath = arg_not_supplied,
        log=logtoscreen("csvFuturesContractPriceData"),
        config: ConfigCsvFuturesPrices = arg_not_supplied
    ):

        super().__init__(log=log)
        self.db = parametricCsvDatabase(log=log, datapath=datapath, config=config)

    def __repr__(self):
        return "csvFuturesContractPricesData accessing %s" % self.datapath

    @property
    def config(self):
        return self.db.config

    @property
    def datapath(self):
        return self.db.datapath

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

    def _get_prices_at_frequency_for_contract_object_no_checking(
        self, contract_object: futuresContract, freq: Frequency
    ) -> futuresContractPrices:
        if freq is not DAILY_PRICE_FREQ:
            raise NotImplementedError("Only daily price data supported currently!")
        return self._get_prices_for_contract_object_no_checking(contract_object)


    def _get_prices_for_contract_object_no_checking(
            self, futures_contract_object: futuresContract) -> futuresContractPrices:
        """
        Read back the prices for a given contract object

        :param contract_object:  futuresContract
        :return: data
        """
        keyname = self._keyname_given_contract_object(futures_contract_object)
        filename = self.db.filename_given_key_name(keyname)

        try:
            instrpricedata = self.db.load_and_process_prices(filename, futures_contract_object.instrument_code)
        except OSError:
            log = futures_contract_object.log(self.log)
            log.warning("Can't find price file %s" % filename)
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
        filename = self.db.filename_given_key_name(keyname)
        futures_price_data.to_csv(
            filename, index_label=self.config.input_date_index_name)


    def _delete_prices_for_contract_object_with_no_checks_be_careful(
        self, futures_contract_object: futuresContract
    ):
        raise NotImplementedError(
            "You can't delete futures prices stored as a csv - Add to overwrite existing data, or delete file manually"
        )


    def has_data_for_contract(self, contract_object: futuresContract) ->bool:
        if self._keyname_given_contract_object(contract_object) in self.db.all_keynames_in_library():
            return True

    def get_contracts_with_price_data(self) ->listOfFuturesContracts:
        """

        :return: list of contracts
        """

        list_of_contract_tuples = self.db.get_contract_tuples_with_price_data()
        list_of_contracts = [
            futuresContract(contract_tuple[0], contract_tuple[1])
            for contract_tuple in list_of_contract_tuples
        ]
        list_of_contracts = listOfFuturesContracts(list_of_contracts)

        return list_of_contracts
