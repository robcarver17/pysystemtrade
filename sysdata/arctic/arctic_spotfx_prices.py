from sysdata.fx.spotfx import fxPricesData
from sysobjects.spot_fx_prices import fxPrices
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

    @property
    def arctic(self):
        return self._arctic

    def __repr__(self):
        return "Arctic connection for spotfx prices, %s/%s @ %s " % (
            self.arctic.database_name,
            self.arctic.collection_name,
            self.arctic.host,
        )

    def get_list_of_fxcodes(self) -> list:
        return self.arctic.get_keynames()

    def _get_fx_prices_without_checking(self, currency_code: str) -> fxPrices:

        fx_data = self.arctic.read(currency_code)

        # Returns a pd.Series which should have the right format
        fx_prices = fxPrices(fx_data['values'])

        return fx_prices

    def _delete_fx_prices_without_any_warning_be_careful(self, currency_code: str):
        self.log.label(currency_code=currency_code)
        self.arctic.delete(currency_code)
        self.log.msg(
            "Deleted fX prices for %s from %s" %
            (currency_code, str(self)), fx_code = currency_code)

    def _add_fx_prices_without_checking_for_existing_entry(
        self, currency_code: str, fx_price_data: fxPrices
    ):
        self.log.label(currency_code=currency_code)
        self.arctic.write(currency_code, pd.Series(fx_price_data))
        self.log.msg(
            "Wrote %s lines of prices for %s to %s"
            % (len(fx_price_data), currency_code, str(self)), fx_code = currency_code
        )
