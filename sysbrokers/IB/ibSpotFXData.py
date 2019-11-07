import pandas as pd
from sysdata.fx.spotfx import fxPricesData, fxPrices
from syslogdiag.log import logtoscreen
from syscore.fileutils import get_filename_for_package

IB_CCY_CONFIG_FILE = get_filename_for_package("sysbrokers.IB.ibConfigSpotFX.csv")

class ibFxPricesData(fxPricesData):

    def __init__(self, ibconnection, log=logtoscreen("ibFxPricesData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB FX price data"

    def _get_fx_prices_without_checking(self, currency_code):
        ccy1, ccy2,invert = self._get_ibfxcode(currency_code)
        raw_fx_prices = self.ibconnection.broker_get_fx_data(ccy1, ccy2=ccy2)

        if invert:
            fx_prices = 1.0/raw_fx_prices
        else:
            fx_prices = raw_fx_prices

        return fx_prices

    def get_list_of_fxcodes(self):
        config_data = self._get_ib_fx_config()
        return list(config_data.CODE)

    def _get_ibfxcode(self, currency_code):
        config_data = self._get_ib_fx_config()
        ccy1 = config_data[config_data.CODE == currency_code].CCY1.values[0]
        ccy2 = config_data[config_data.CODE == currency_code].CCY2.values[0]
        invert = config_data[config_data.CODE == currency_code].INVERT.values[0] == "YES"

        return ccy1, ccy2,invert

    def _get_ib_fx_config(self):
        try:
            config_data=pd.read_csv(IB_CCY_CONFIG_FILE)
        except:
            raise Exception("Can't read file %s" % IB_CCY_CONFIG_FILE)

        return config_data

