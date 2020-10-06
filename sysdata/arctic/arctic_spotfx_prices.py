from sysdata.fx.spotfx import fxPrices, fxPricesData
from sysdata.arctic.arctic_connection import articConnection
from syslogdiag.log import logtoscreen
import pandas as pd

SPOTFX_COLLECTION = "spotfx_prices"


class arcticFxPricesData(fxPricesData):
    """
    Class to read / write fx prices
    """

    def __init__(self, mongo_db=None, log=logtoscreen("arcticFxPricesData")):

        super().__init__(log=log)

        self._arctic = articConnection(SPOTFX_COLLECTION, mongo_db=mongo_db)

        self.name = "Arctic connection for spotfx prices, %s/%s @ %s " % (
            self._arctic.database_name,
            self._arctic.collection_name,
            self._arctic.host,
        )

    def __repr__(self):
        return self.name

    def get_list_of_fxcodes(self):
        return self._arctic.library.list_symbols()

    def _get_fx_prices_without_checking(self, currency_code):

        item = self._arctic.library.read(currency_code)

        # Returns a pd.Series which should have the right format
        data = item.data
        fx_prices = fxPrices(data)

        return fx_prices

    def _delete_fx_prices_without_any_warning_be_careful(self, currency_code):
        self.log.label(currency_code=currency_code)
        self._arctic.library.delete(currency_code)
        self.log.msg(
            "Deleted fX prices for %s from %s" %
            (currency_code, self.name))

    def _add_fx_prices_without_checking_for_existing_entry(
        self, currency_code, fx_price_data
    ):
        self.log.label(currency_code=currency_code)
        self._arctic.library.write(currency_code, pd.Series(fx_price_data))
        self.log.msg(
            "Wrote %s lines of prices for %s to %s"
            % (len(fx_price_data), currency_code, self.name)
        )
