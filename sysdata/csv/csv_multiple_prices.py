from sysdata.futures.multiple_prices import (
    futuresMultiplePricesData,
)
from sysobjects.multiple_prices import futuresMultiplePrices

from syscore.fileutils import get_filename_for_package, files_with_extension_in_pathname
from syscore.pdutils import pd_readcsv
from syscore.genutils import str_of_int
from syslogdiag.log import logtoscreen

CSV_MULTIPLE_PRICE_DIRECTORY = "data.futures.multiple_prices_csv"
DATE_INDEX_NAME = "DATETIME"


class csvFuturesMultiplePricesData(futuresMultiplePricesData):
    """

    Class for roll calendars write / to from csv
    """

    def __init__(self, datapath=None, log=logtoscreen(
            "csvFuturesMultiplePricesData")):

        super().__init__(log=log)

        if datapath is None:
            datapath = CSV_MULTIPLE_PRICE_DIRECTORY

        self._datapath = datapath


    def __repr__(self):
        return "csvFuturesMultiplePricesData accessing %s" % self._datapath

    def get_list_of_instruments(self):
        return files_with_extension_in_pathname(self._datapath, ".csv")

    def _get_multiple_prices_without_checking(self, instrument_code):
        filename = self._filename_given_instrument_code(instrument_code)

        try:
            instr_all_price_data = pd_readcsv(
                filename, date_index_name=DATE_INDEX_NAME)
        except OSError:
            self.log.warning("Can't find multiple price file %s" % filename)
            return futuresMultiplePrices.create_empty()

        instr_all_price_data.CARRY_CONTRACT = instr_all_price_data.CARRY_CONTRACT.apply(
            str_of_int)
        instr_all_price_data.PRICE_CONTRACT = instr_all_price_data.PRICE_CONTRACT.apply(
            str_of_int)
        instr_all_price_data.FORWARD_CONTRACT = (
            instr_all_price_data.FORWARD_CONTRACT.apply(str_of_int)
        )

        return futuresMultiplePrices(instr_all_price_data)

    def _delete_multiple_prices_without_any_warning_be_careful(
            instrument_code):
        raise NotImplementedError(
            "You can't delete multiple prices stored as a csv - Add to overwrite existing or delete file manually"
        )

    def _add_multiple_prices_without_checking_for_existing_entry(
        self, instrument_code, multiple_price_data
    ):

        filename = self._filename_given_instrument_code(instrument_code)
        multiple_price_data.to_csv(filename, index_label=DATE_INDEX_NAME)

    def _filename_given_instrument_code(self, instrument_code):
        filename = get_filename_for_package(
            self._datapath, "%s.csv" % (instrument_code)
        )

        return filename
