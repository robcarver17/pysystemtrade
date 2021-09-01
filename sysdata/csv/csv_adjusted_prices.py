import pandas as pd

from sysdata.futures.adjusted_prices import (
    futuresAdjustedPricesData,
)
from sysobjects.adjusted_prices import futuresAdjustedPrices
from sysdata.csv.parametric_csv_database import parametricCsvDatabase, ConfigCsvFuturesPrices
from syscore.objects import arg_not_supplied, missing_data
from syslogdiag.log_to_screen import logtoscreen
from sysobjects.futures_per_contract_prices import FINAL_COLUMN

ADJUSTED_PRICES_DIRECTORY = "data.futures.adjusted_prices_csv"
DATE_INDEX_NAME = "DATETIME"

DEFAULT_ADJUSTED_FILENAME_FORMAT = "%{IC}.csv" # e.g. CRUDE_W.csv

class csvFuturesAdjustedPricesData(futuresAdjustedPricesData):
    """
    Class for adjusted prices write / to from csv
    """

    def __init__(self, datapath=arg_not_supplied, log=logtoscreen(
            "csvFuturesContractPriceData"), config:ConfigCsvFuturesPrices = arg_not_supplied ):

        super().__init__(log=log)

        if datapath is arg_not_supplied:
            datapath = ADJUSTED_PRICES_DIRECTORY

        if config is arg_not_supplied:
            config = ConfigCsvFuturesPrices(continuous_contracts=True, input_filename_format=DEFAULT_ADJUSTED_FILENAME_FORMAT)

        self.db = parametricCsvDatabase(log=log, datapath=datapath, config=config)


    def __repr__(self):
        return "csvFuturesAdjustedPricesData accessing %s" % self.datapath

    @property
    def datapath(self):
        return self.db.datapath

    def get_list_of_instruments(self) -> list:
        return self.db.get_list_of_instrument_codes()

    def _get_adjusted_prices_without_checking(self, instrument_code: str) -> futuresAdjustedPrices:
        filename = self.db.filename_given_instrument_code(instrument_code)

        try:
            instrpricedata = self.db.load_and_process_prices(filename, instrument_code)
        except OSError:
            self.log.warning("Can't find adjusted price file %s" % filename)
            return futuresAdjustedPrices.create_empty()

        if len(instrpricedata.columns) > 1:
            # discard all other columns  
            instrpricedata = pd.DataFrame( instrpricedata[FINAL_COLUMN])
        instrpricedata.columns = ["price"]
        instrpricedata = instrpricedata.groupby(level=0).last()
        instrpricedata = pd.Series(instrpricedata.iloc[:, 0])

        instrpricedata = futuresAdjustedPrices(instrpricedata)

        return instrpricedata

    def get_adjusted_prices_as_pd(self, instrument_code: str) -> pd.DataFrame:
        """
        Get adjusted prices as Pandas dataframe. If original OPEN/HIGH/LOW/FINAL data are available then keep them unchanged.

        :param instrument_code: self-explanatory
        :return: DataFrame containing all available columns (etc. OPEN/HIGH/LOW/FINAL or price)
        """
        if not self.is_code_in_data(instrument_code):
            return missing_data

        filename = self.db.filename_given_instrument_code(instrument_code)
        try:
            instrpricedata = self.db.load_and_process_prices(filename, instrument_code)
        except OSError:
            self.log.warning("Can't find adjusted price file %s" % filename)
            return missing_data

        instrpricedata = instrpricedata.groupby(level=0).last()
        return instrpricedata


    def _delete_adjusted_prices_without_any_warning_be_careful(
            self, instrument_code: str):
        raise NotImplementedError(
            "You can't delete adjusted prices stored as a csv - Add to overwrite existing or delete file manually"
        )

    def _add_adjusted_prices_without_checking_for_existing_entry(
        self, instrument_code:str, adjusted_price_data: futuresAdjustedPrices
    ):

        # Ensures the file will be written with a column header
        adjusted_price_data_as_dataframe = pd.DataFrame(adjusted_price_data)
        adjusted_price_data_as_dataframe.columns = ["price"]

        filename = self.db.filename_given_instrument_code(instrument_code)
        adjusted_price_data_as_dataframe.to_csv(
            filename, index_label=DATE_INDEX_NAME)

