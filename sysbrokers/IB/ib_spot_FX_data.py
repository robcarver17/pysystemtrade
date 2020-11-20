from collections import  namedtuple
import pandas as pd
from sysdata.fx.spotfx import fxPricesData
from sysobjects.spot_fx_prices import fxPrices
from syslogdiag.log import logtoscreen
from syscore.fileutils import get_filename_for_package
from syscore.objects import missing_file, missing_instrument

IB_CCY_CONFIG_FILE = get_filename_for_package(
    "sysbrokers.IB.ib_config_spot_FX.csv")

ibFXConfig = namedtuple("ibFXConfig", ["ccy1", "ccy2", "invert"])

class ibFxPricesData(fxPricesData):
    def __init__(self, ibconnection, log=logtoscreen("ibFxPricesData")):
        self._ibconnection = ibconnection
        super().__init__(log=log)

    def __repr__(self):
        return "IB FX price data"

    @property
    def ibconnection(self):
        return self._ibconnection


    def get_list_of_fxcodes(self) -> list:
        config_data = self._get_ib_fx_config()
        if config_data is missing_file:
            self.log.warn(
                "Can't get list of fxcodes for IB as config file missing")
            return []

        list_of_codes = list(config_data.CODE)

        return list_of_codes

    def _get_fx_prices_without_checking(self, currency_code: str) -> fxPrices:
        ib_config_for_code = self._get_config_info_for_code(currency_code)
        if ib_config_for_code is missing_instrument:
            self.warn(
                "Can't get prices as missing IB config for %s" %
                currency_code, fx_code=currency_code)
            return fxPrices.create_empty()

        data = self._get_fx_prices_with_ib_config(currency_code, ib_config_for_code)

        return data

    def _get_fx_prices_with_ib_config(self, currency_code: str, ib_config_for_code: ibFXConfig) ->fxPrices:
        raw_fx_prices_as_series = self._get_raw_fx_prices(ib_config_for_code)

        if len(raw_fx_prices_as_series) == 0:
            self.log.warn("No available IB prices for %s %s" % (currency_code, str(ib_config_for_code))
                          , fx_code = currency_code )
            return fxPrices.create_empty()

        if ib_config_for_code.invert:
            raw_fx_prices = 1.0 / raw_fx_prices_as_series
        else:
            raw_fx_prices = raw_fx_prices_as_series

        # turn into a fxPrices
        fx_prices = fxPrices(raw_fx_prices)

        self.log.msg("Downloaded %d prices" % len(fx_prices), fx_code = currency_code)

        return fx_prices

    def _get_raw_fx_prices(self, ib_config_for_code: ibFXConfig) -> pd.Series:
        raw_fx_prices = self.ibconnection.broker_get_daily_fx_data(
            ib_config_for_code.ccy1, ccy2=ib_config_for_code.ccy2
        )
        raw_fx_prices_as_series = raw_fx_prices["FINAL"]

        return raw_fx_prices_as_series


    def _get_config_info_for_code(self, currency_code: str) -> ibFXConfig:
        new_log = self.log.setup(currency_code=currency_code)

        config_data = self._get_ib_fx_config()
        if config_data is missing_file:
            new_log.warn(
                "Can't get IB FX config for %s as config file missing" %
                currency_code, fx_code = currency_code)

            return missing_instrument

        ccy1 = config_data[config_data.CODE == currency_code].CCY1.values[0]
        ccy2 = config_data[config_data.CODE == currency_code].CCY2.values[0]
        invert = (config_data[config_data.CODE ==
                              currency_code].INVERT.values[0] == "YES")

        ib_config_for_code = ibFXConfig(ccy1, ccy2, invert)

        return ib_config_for_code

    # Configuration read in and cache
    def _get_ib_fx_config(self) ->pd.DataFrame:
        config = getattr(self, "_config", None)
        if config is None:
            config = self._get_and_set_ib_config_from_file()

        return config

    def _get_and_set_ib_config_from_file(self) ->pd.DataFrame:

        try:
            config_data = pd.read_csv(IB_CCY_CONFIG_FILE)
        except BaseException:
            self.log.warn("Can't read file %s" % IB_CCY_CONFIG_FILE)
            config_data = missing_file

        self._config = config_data

        return config_data

    def update_fx_prices(self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def add_fx_prices(self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def _delete_fx_prices_without_any_warning_be_careful(
            self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def _add_fx_prices_without_checking_for_existing_entry(
            self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")