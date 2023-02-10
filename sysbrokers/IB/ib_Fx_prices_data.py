from collections import namedtuple
import pandas as pd

from sysbrokers.IB.client.ib_fx_client import ibFxClient
from sysbrokers.broker_fx_prices_data import brokerFxPricesData
from syscore.exceptions import missingData
from sysdata.data_blob import dataBlob
from sysobjects.spot_fx_prices import fxPrices
from syslogdiag.log_to_screen import logtoscreen
from syscore.fileutils import resolve_path_and_filename_for_package
from syscore.constants import missing_instrument, missing_file

IB_CCY_CONFIG_FILE = resolve_path_and_filename_for_package(
    "sysbrokers.IB.ib_config_spot_FX.csv"
)

ibFXConfig = namedtuple("ibFXConfig", ["ccy1", "ccy2", "invert"])


class ibFxPricesData(brokerFxPricesData):
    def __init__(self, ibconnection, data: dataBlob, log=logtoscreen("ibFxPricesData")):
        super().__init__(log=log, data=data)
        self._ibconnection = ibconnection
        self._dataBlob = data

    def __repr__(self):
        return "IB FX price data"

    @property
    def ibconnection(self):
        return self._ibconnection

    @property
    def ib_client(self) -> ibFxClient:
        client = getattr(self, "_ib_client", None)
        if client is None:
            client = self._ib_client = ibFxClient(
                ibconnection=self.ibconnection, log=self.log
            )

        return client

    def get_list_of_fxcodes(self) -> list:
        config_data = self._get_ib_fx_config()
        if config_data is missing_file:
            self.log.warn("Can't get list of fxcodes for IB as config file missing")
            return []

        list_of_codes = list(config_data.CODE)

        return list_of_codes

    def _get_fx_prices_without_checking(self, currency_code: str) -> fxPrices:
        ib_config_for_code = self._get_config_info_for_code(currency_code)
        if ib_config_for_code is missing_instrument:
            self.log.warn(
                "Can't get prices as missing IB config for %s" % currency_code,
                fx_code=currency_code,
            )
            return fxPrices.create_empty()

        data = self._get_fx_prices_with_ib_config(currency_code, ib_config_for_code)

        return data

    def _get_fx_prices_with_ib_config(
        self, currency_code: str, ib_config_for_code: ibFXConfig
    ) -> fxPrices:
        raw_fx_prices_as_series = self._get_raw_fx_prices(ib_config_for_code)

        if len(raw_fx_prices_as_series) == 0:
            self.log.warn(
                "No available IB prices for %s %s"
                % (currency_code, str(ib_config_for_code)),
                fx_code=currency_code,
            )
            return fxPrices.create_empty()

        if ib_config_for_code.invert:
            raw_fx_prices = 1.0 / raw_fx_prices_as_series
        else:
            raw_fx_prices = raw_fx_prices_as_series

        # turn into a fxPrices
        fx_prices = fxPrices(raw_fx_prices)

        self.log.msg("Downloaded %d prices" % len(fx_prices), fx_code=currency_code)

        return fx_prices

    def _get_raw_fx_prices(self, ib_config_for_code: ibFXConfig) -> pd.Series:
        ccy1 = ib_config_for_code.ccy1
        ccy2 = ib_config_for_code.ccy2

        try:
            raw_fx_prices = self.ib_client.broker_get_daily_fx_data(ccy1, ccy2)
        except missingData:
            return pd.Series()
        raw_fx_prices_as_series = raw_fx_prices["FINAL"]

        return raw_fx_prices_as_series

    def _get_config_info_for_code(self, currency_code: str) -> ibFXConfig:
        new_log = self.log.setup(currency_code=currency_code)

        config_data = self._get_ib_fx_config()
        if config_data is missing_file:
            new_log.warn(
                "Can't get IB FX config for %s as config file missing" % currency_code,
                fx_code=currency_code,
            )

            return missing_instrument

        ccy1 = config_data[config_data.CODE == currency_code].CCY1.values[0]
        ccy2 = config_data[config_data.CODE == currency_code].CCY2.values[0]
        invert = (
            config_data[config_data.CODE == currency_code].INVERT.values[0] == "YES"
        )

        ib_config_for_code = ibFXConfig(ccy1, ccy2, invert)

        return ib_config_for_code

    # Configuration read in and cache
    def _get_ib_fx_config(self) -> pd.DataFrame:
        config = getattr(self, "_config", None)
        if config is None:
            config = self._get_and_set_ib_config_from_file()

        return config

    def _get_and_set_ib_config_from_file(self) -> pd.DataFrame:

        try:
            config_data = pd.read_csv(IB_CCY_CONFIG_FILE)
        except BaseException:
            self.log.warn("Can't read file %s" % IB_CCY_CONFIG_FILE)
            config_data = missing_file

        self._config = config_data

        return config_data
