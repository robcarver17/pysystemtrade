"""
Read and write data from mongodb for 'multiple prices'

"""
import pandas as pd
from sysdata.arctic.arctic_connection import articConnection
from sysdata.futures.multiple_prices import (
    futuresMultiplePricesData,
    futuresMultiplePrices,
    list_of_contract_column_names,
    list_of_price_column_names,
)
from syslogdiag.log import logtoscreen

MULTIPLE_COLLECTION = "futures_multiple_prices"


class arcticFuturesMultiplePricesData(futuresMultiplePricesData):
    """
    Class to read / write multiple futures price data to and from arctic
    """

    def __init__(
        self, mongo_db=None, log=logtoscreen("arcticFuturesMultiplePricesData")
    ):

        super().__init__(log=log)

        self._arctic = articConnection(MULTIPLE_COLLECTION, mongo_db=mongo_db)

        self.name = (
            "simData connection for multiple futures prices, arctic %s/%s @ %s " %
            (self._arctic.database_name,
             self._arctic.collection_name,
             self._arctic.host,
             ))

    def __repr__(self):
        return self.name

    def get_list_of_instruments(self):
        return self._arctic.library.list_symbols()

    def _get_multiple_prices_without_checking(self, instrument_code):
        item = self._arctic.library.read(instrument_code)

        # Returns a data frame which should have the right format
        data = item.data

        return futuresMultiplePrices(data)

    def _delete_multiple_prices_without_any_warning_be_careful(
            self, instrument_code):
        self.log.label(instrument_code=instrument_code)
        self._arctic.library.delete(instrument_code)
        self.log.msg(
            "Deleted multiple prices for %s from %s" %
            (instrument_code, self.name))

    def _add_multiple_prices_without_checking_for_existing_entry(
        self, instrument_code, multiple_price_data_object
    ):

        multiple_price_data_aspd = pd.DataFrame(multiple_price_data_object)

        for contract_column in list_of_contract_column_names:
            multiple_price_data_aspd[contract_column] = multiple_price_data_aspd[
                contract_column
            ].astype(str)

        for price_column in list_of_price_column_names:
            multiple_price_data_aspd[price_column] = multiple_price_data_aspd[
                price_column
            ].astype(float)

        self.log.label(instrument_code=instrument_code)
        self._arctic.library.write(instrument_code, multiple_price_data_aspd)
        self.log.msg(
            "Wrote %s lines of prices for %s to %s"
            % (len(multiple_price_data_aspd), instrument_code, self.name)
        )
