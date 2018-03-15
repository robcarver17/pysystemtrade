import pandas as pd

from sysdata.fx.spotfx import fxPricesData, fxPrices
from syscore.fileutils import get_filename_for_package, files_with_extension_in_pathname
from syscore.pdutils import pd_readcsv


FX_PRICES_DIRECTORY = "data.futures.fx_prices_csv"
DATE_INDEX_NAME = "DATETIME"


class csvFxPricesData(fxPricesData):
    """

    Class for fx prices write / to from csv
    """

    def __init__(self, datapath=None):

        super().__init__()

        if datapath is None:
            datapath = FX_PRICES_DIRECTORY

        self._datapath = datapath

    def __repr__(self):
        return "csvFxPricesData accessing %s" % self._datapath

    def get_list_of_fxcodes(self):
        return files_with_extension_in_pathname(self._datapath, ".csv")

    def _get_fx_prices_without_checking(self, code):
        filename = self._filename_given_fx_code(code)
        try:
            fx_data = pd_readcsv(filename)
        except OSError:
            self.log.warning("Can't find currency price file %s" % filename)
            return fxPrices.create_empty()

        fx_data = pd.Series(fx_data.iloc[:, 0])

        fx_data = fxPrices(fx_data)

        return fx_data


    def _delete_fx_prices_without_any_warning_be_careful(code):
        raise NotImplementedError("You can't delete adjusted prices stored as a csv - Add to overwrite existing or delete file manually")

    def _add_fx_prices_without_checking_for_existing_entry(self, code, fx_price_data):
        filename = self._filename_given_fx_code(code)
        fx_price_data.to_csv(filename, index_label = DATE_INDEX_NAME)


    def _filename_given_fx_code(self, code):
        return get_filename_for_package("%s.%s.csv" %(self._datapath,code))



