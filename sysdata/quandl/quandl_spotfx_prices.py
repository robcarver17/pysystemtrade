"""
DEPRECATED: DOESN'T WORK ANY MORE
"""

import quandl
import pandas as pd
from sysdata.quandl.quandl_utils import load_private_key
from sysdata.fx.spotfx import fxPricesData, fxPrices
from syscore.fileutils import get_filename_for_package

quandl.ApiConfig.api_key = load_private_key()

NOT_IN_QUANDL_MSG = "You can't add, delete, or get a list of codes for Quandl FX data"
QUANDL_CCY_CONFIG_FILE = get_filename_for_package(
    "sysdata.quandl.QuandlFXConfig.csv")


class quandlFxPricesData(fxPricesData):
    def __repr__(self):
        return "Quandl FX price data"

    def _get_fx_prices_without_checking(self, currency_code):
        qcode = self._get_qcode(currency_code)
        try:
            fx_prices = quandl.get(qcode)
        except Exception as exception:
            self.log.warn(
                "Can't get QUANDL data for %s error %s" %
                (qcode, exception))
            return fxPrices.create_empty()

        fx_prices = fx_prices.Rate

        return fxPrices(fx_prices)

    def get_list_of_fxcodes(self):
        config_data = self._get_quandl_fx_config()
        return list(config_data.CODE)

    def _get_qcode(self, currency_code):
        config_data = self._get_quandl_fx_config()
        qcode = config_data[config_data.CODE == currency_code].QCODE.values[0]

        return qcode

    def _get_quandl_fx_config(self):
        try:
            config_data = pd.read_csv(QUANDL_CCY_CONFIG_FILE)
        except BaseException:
            raise Exception("Can't read file %s" % QUANDL_CCY_CONFIG_FILE)

        return config_data
