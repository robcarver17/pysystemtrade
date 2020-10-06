import pandas as pd
from copy import copy

from sysdata.fx.spotfx import fxPricesData, fxPrices
from syscore.fileutils import get_filename_for_package, files_with_extension_in_pathname
from syscore.pdutils import pd_readcsv, DEFAULT_DATE_FORMAT
from syslogdiag.log import logtoscreen

FX_PRICES_DIRECTORY = "data.futures.fx_prices_csv"


class csvFxPricesData(fxPricesData):
    """

    Class for fx prices write / to from csv
    """

    def __init__(
        self,
        datapath=None,
        log=logtoscreen("csvFxPricesData"),
        price_column="PRICE",
        date_column="DATETIME",
        date_format=DEFAULT_DATE_FORMAT,
    ):
        """
        Get FX data from a .csv file

        :param datapath: Path where csv files are located
        :param log: logging object
        :param price_column: Column where spot FX prices are
        :param date_column: Column where dates are
        :param date_format: Format for dates https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
        """

        super().__init__(log=log)

        if datapath is None:
            datapath = FX_PRICES_DIRECTORY

        self._datapath = datapath
        self._price_column = price_column
        self._date_column = date_column
        self._date_format = date_format

    def __repr__(self):
        return "csvFxPricesData accessing %s" % self._datapath

    def get_list_of_fxcodes(self):
        return files_with_extension_in_pathname(self._datapath, ".csv")

    def _get_fx_prices_without_checking(self, code):
        filename = self._filename_given_fx_code(code)
        price_column = self._price_column
        date_column = self._date_column
        date_format = self._date_format

        try:
            fx_data = pd_readcsv(
                filename, date_format=date_format, date_index_name=date_column
            )
        except OSError:
            self.log.warn("Can't find currency price file %s" % filename)
            return fxPrices.create_empty()

        fx_data = pd.Series(fx_data[price_column])

        fx_data = fxPrices(fx_data.sort_index())

        return fx_data

    def _delete_fx_prices_without_any_warning_be_careful(code):
        raise NotImplementedError(
            "You can't delete adjusted prices stored as a csv - Add to overwrite existing or delete file manually"
        )

    def _add_fx_prices_without_checking_for_existing_entry(
            self, code, fx_price_data):
        filename = self._filename_given_fx_code(code)
        price_column = self._price_column
        date_column = self._date_column
        date_format = self._date_format

        fx_price_data.name = price_column
        fx_price_data.to_csv(
            filename,
            index_label=date_column,
            date_format=date_format,
            header=True)

    def _filename_given_fx_code(self, code):
        return get_filename_for_package(self._datapath, "%s.csv" % (code))
