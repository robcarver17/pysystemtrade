"""
Get data from quandl

"""

from sysdata.futuresdata import FuturesContract
from syscore.dateutils import contract_month_from_number
from syscore.fileutils import get_filename_for_package

import quandl
import os
import pandas as pd

QUANDL_FUTURES_CONFIG_FILE = get_filename_for_package("sysdata.quandl.QuandlFuturesConfig.csv")

#quandl.ApiConfig.api_key = "YOUR_KEY_HERE"

def quandl_get_futures_contract_historic_data(futures_contract):
    """
    Get the data from quandl for a specific futures contract

    :param futures_contract:
    :return: pd.DataFrame
    """

    quandl_contract = quandlFuturesContract(futures_contract)

    return quandl.get(quandl_contract.quandl_identifier())



class quandlFuturesContract(FuturesContract):
    """
    An individual futures contract, with additional Quandl methods
    """

    def __init__(self, futures_contract):
        """
        We always create a quandl contract from an existing, normal, contract

        :param futures_contract: of type FuturesContract
        """

        super().__init__(futures_contract.instrument_code, futures_contract.contract_month)

    def quandl_identifier(self):
        """
        Returns the Quandl identifier for a given contract

        :return: str
        """

        quandl_year = self.contract_month[:4]
        quandl_month = contract_month_from_number(int(self.contract_month[4:]))

        quandl_date_id = quandl_month + quandl_year

        market = self.get_quandlmarket_for_instrument()
        codename = self.get_quandlcode_for_instrument()

        quandldef = '%s/%s%s' % (market, codename, quandl_date_id)

        return quandldef

    def _get_config_information(self):
        """
        Get configuration information

        :return: dict of config information relating to self.instrument_code
        """

        config_data=pd.read_csv(QUANDL_FUTURES_CONFIG_FILE)
        config_data.index = config_data.CODE
        config_data.drop("CODE", 1, inplace=True)

        return config_data.loc[self.instrument_code]

    def get_quandlcode_for_instrument(self):

        config = self._get_config_information()

        return config.QCODE

    def get_quandlmarket_for_instrument(self):

        config = self._get_config_information()

        return config.MARKET

