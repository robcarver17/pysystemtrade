import pandas as pd

from sysbrokers.IB.client.ib_fx_client import ibFxClient
from sysbrokers.IB.config.ib_fx_config import (
    get_ib_config_from_file,
    config_info_for_code,
    get_list_of_codes,
    ibFXConfig,
)
from sysbrokers.broker_fx_prices_data import brokerFxPricesData
from syscore.exceptions import missingData, missingInstrument
from sysdata.data_blob import dataBlob
from sysobjects.spot_fx_prices import fxPrices
from syslogging.logger import *


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
        list_of_codes = get_list_of_codes(log=list, config_data=config_data)

        return list_of_codes

    def _get_fx_prices_without_checking(self, currency_code: str) -> fxPrices:
        try:
            ib_config_for_code = self._get_config_info_for_code(currency_code)
        except missingInstrument:
            log = self.log.setup(**{CURRENCY_CODE_LOG_LABEL: currency_code})
            log.warn("Can't get prices as missing IB config for %s" % currency_code)
            return fxPrices.create_empty()

        data = self._get_fx_prices_with_ib_config(currency_code, ib_config_for_code)

        return data

    def _get_fx_prices_with_ib_config(
        self, currency_code: str, ib_config_for_code: ibFXConfig
    ) -> fxPrices:
        raw_fx_prices_as_series = self._get_raw_fx_prices(ib_config_for_code)

        log = self.log.setup(**{CURRENCY_CODE_LOG_LABEL: currency_code})

        if len(raw_fx_prices_as_series) == 0:
            log.warn(
                "No available IB prices for %s %s"
                % (currency_code, str(ib_config_for_code))
            )
            return fxPrices.create_empty()

        if ib_config_for_code.invert:
            raw_fx_prices = 1.0 / raw_fx_prices_as_series
        else:
            raw_fx_prices = raw_fx_prices_as_series

        # turn into a fxPrices
        fx_prices = fxPrices(raw_fx_prices)

        log.debug("Downloaded %d prices" % len(fx_prices))

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

        config_data = self._get_ib_fx_config()
        ib_config_for_code = config_info_for_code(
            config_data=config_data, log=self.log, currency_code=currency_code
        )

        return ib_config_for_code

    # Configuration read in and cache
    def _get_ib_fx_config(self) -> pd.DataFrame:
        config = getattr(self, "_config", None)
        if config is None:
            config = self._get_and_set_ib_config_from_file()

        return config

    def _get_and_set_ib_config_from_file(self) -> pd.DataFrame:

        config_data = get_ib_config_from_file(log=self.log)
        self._config = config_data

        return config_data
