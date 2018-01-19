"""
Get data from quandl

"""

from sysdata.futuresdata import futuresContract, listOfFuturesContracts, futuresData
from syscore.fileutils import get_filename_for_package

import quandl
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

    contract_data = quandl.get(quandl_contract.quandl_identifier())

    return quandlFuturesContract(futures_contract, contract_data)

class quandlFuturesData(futuresData):
    """
    Parses Quandl format into our format

    Does any transformations needed to price etc
    """
    def __init__(self, futures_contract, contract_data):

        new_data = pd.DataFrame(dict(OPEN = contract_data.Open,
                                     CLOSE = contract_data.Close,
                                     HIGH = contract_data.High,
                                     LOW = contract_data.Low,
                                     SETTLE = contract_data.Settle,
                                     VOLUME = contract_data.Volume,
                                     OPEN_INTEREST = contract_data['Prev. Day Open Interest']))

        super().__init__(self, new_data)


class listOfQuandlFuturesContracts(listOfFuturesContracts):

    def __init__(self, list_of_contracts):
        """
        We always create from a list of normal contracts
        """

        list_of_contracts = [quandlFuturesContract(contract) for contract in list_of_contracts]

        super().__init__(list_of_contracts)

class quandlFuturesContract(futuresContract):
    """
    An individual futures contract, with additional Quandl methods
    """

    def __init__(self, futures_contract):
        """
        We always create a quandl contract from an existing, normal, contract

        :param futures_contract: of type FuturesContract
        """

        super().__init__(futures_contract.instrument, futures_contract.date)

    def quandl_identifier(self):
        """
        Returns the Quandl identifier for a given contract

        :return: str
        """

        quandl_year = str(self.date.year())
        quandl_month = self.date.letter_month()

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

