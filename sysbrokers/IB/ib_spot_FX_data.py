import pandas as pd
from sysdata.fx.spotfx import fxPricesData, fxPrices
from syslogdiag.log import logtoscreen
from syscore.fileutils import get_filename_for_package
from syscore.objects import missing_file, missing_instrument

IB_CCY_CONFIG_FILE = get_filename_for_package(
    "sysbrokers.IB.ib_config_spot_FX.csv")


class ibFxPricesData(fxPricesData):
    def __init__(self, ibconnection, log=logtoscreen("ibFxPricesData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB FX price data"

    def _get_fx_prices_without_checking(self, currency_code):
        new_log = self.log.setup(currency_code=currency_code)

        ibfxcode = self._get_ibfxcode(currency_code)
        if ibfxcode is missing_instrument:
            new_log.warn(
                "Can't get prices as missing IB config for %s" %
                currency_code)
            return fxPrices.create_empty()

        ccy1, ccy2, invert = ibfxcode
        raw_fx_prices = self.ibconnection.broker_get_daily_fx_data(
            ccy1, ccy2=ccy2, bar_freq="D"
        )
        raw_fx_prices_as_series = raw_fx_prices["FINAL"]

        if len(raw_fx_prices_as_series) == 0:
            new_log.warn("No available IB prices for %s" % currency_code)
            return fxPrices.create_empty()

        # turn into a fxPrices
        raw_fx_prices = fxPrices(raw_fx_prices_as_series)

        if invert:
            fx_prices = 1.0 / raw_fx_prices
        else:
            fx_prices = raw_fx_prices

        new_log.msg("Downloaded %d prices" % len(fx_prices))

        return fx_prices

    def get_list_of_fxcodes(self):
        config_data = self._get_ib_fx_config()
        if config_data is missing_file:
            self.log.warn(
                "Can't get list of fxcodes for IB as config file missing")
            return []

        list_of_codes = list(config_data.CODE)

        return list_of_codes

    def _get_ibfxcode(self, currency_code):
        new_log = self.log.setup(currency_code=currency_code)

        config_data = self._get_ib_fx_config()
        if config_data is missing_file:
            new_log.warn(
                "Can't get IB FX config for %s as config file missing" %
                currency_code)

            return missing_instrument

        ccy1 = config_data[config_data.CODE == currency_code].CCY1.values[0]
        ccy2 = config_data[config_data.CODE == currency_code].CCY2.values[0]
        invert = (config_data[config_data.CODE ==
                              currency_code].INVERT.values[0] == "YES")

        return ccy1, ccy2, invert

    # Configuration read in and cache
    def _get_ib_fx_config(self):
        config = getattr(self, "_config", None)
        if config is None:
            config = self._get_and_set_ib_config_from_file()

        return config

    def _get_and_set_ib_config_from_file(self):

        try:
            config_data = pd.read_csv(IB_CCY_CONFIG_FILE)
        except BaseException:
            self.log.warn("Can't read file %s" % IB_CCY_CONFIG_FILE)
            config_data = missing_file

        self._config = config_data

        return config_data

    def update_fx_prices(self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def _delete_fx_prices_without_any_warning_be_careful(
            self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def add_fx_prices(self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")
