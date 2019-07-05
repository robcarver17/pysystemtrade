"""
Get data from barchart for futures

"""

from sysdata.futures.contracts import futuresContract
from sysdata.futures.futures_per_contract_prices import futuresContractPriceData, futuresContractPrices
from syscore.fileutils import get_filename_for_package
from sysdata.barchart.barchart_utils import load_private_key

import ondemand
import pandas as pd


BARCHART_FUTURES_CONFIG_FILE = get_filename_for_package("sysdata.barchart.barchartFuturesConfig.csv")


od = ondemand.OnDemandClient(api_key=load_private_key()) # ondemand API key
# quotes=od.history('GCG19', historical_type = 'daily')['results']
# pd.DataFrame(quotes)

class barchartFuturesConfiguration(object):

    def __init__(self, config_file = BARCHART_FUTURES_CONFIG_FILE):

        self._config_file = config_file

    def get_list_of_instruments(self):
        config_data = self._get_config_information()

        return list(config_data.index)

    def get_instrument_config(self, instrument_code):

        if instrument_code not in self.get_list_of_instruments():
            raise Exception("Instrument %s missing from config file %s" % (instrument_code, self._config_file))

        config_data = self._get_config_information()
        data_for_code = config_data.loc[instrument_code]

        return data_for_code


    def _get_config_information(self):
        """
        Get configuration information

        :return: dict of config information relating to self.instrument_code
        """

        try:
            config_data=pd.read_csv(self._config_file)
        except:
            raise Exception("Can't read file %s" % self._config_file)

        try:
            config_data.index = config_data.CODE
            config_data.drop("CODE", 1, inplace=True)

        except:
            raise Exception("Badly configured file %s" %
                            (self._config_file))

        return config_data

    def get_barchartcode_for_instrument(self, instrument_code):

        config = self.get_instrument_config(instrument_code)
        return config.BCODE

    def get_barchartmarket_for_instrument(self, instrument_code):

        config = self.get_instrument_config(instrument_code)
        return config.MARKET

    def get_first_contract_date(self, instrument_code):

        config = self.get_instrument_config(instrument_code)
        start_date = config.FIRST_CONTRACT

        return "%d" % start_date

    def get_barchart_dividing_factor(self, instrument_code):

        config = self.get_instrument_config(instrument_code)
        factor = config.FACTOR

        return float(factor)


USE_DEFAULT = object()

class _barchartFuturesContract(futuresContract):
    """
    An individual futures contract, with additional Barchart methods
    """

    def __init__(self, futures_contract, barchart_instrument_data = USE_DEFAULT):
        """
        We always create a barchart contract from an existing, normal, contract

        :param futures_contract: of type FuturesContract
        """

        super().__init__(futures_contract.instrument, futures_contract.contract_date)

        if barchart_instrument_data is USE_DEFAULT:
            barchart_instrument_data = barchartFuturesConfiguration()

        self._barchart_instrument_data = barchart_instrument_data

    def barchart_identifier(self):
        """
        Returns the Barchart identifier for a given contract

        :return: str
        """

        barchart_year = str(self.contract_date.year())
        barchart_month = self.contract_date.letter_month()

        try:
            barchart_date_id = barchart_month + barchart_year[2:4]

            # market = self.get_barchartmarket_for_instrument()
            codename = self.get_barchartcode_for_instrument()

            # barchartdef = '%s/%s%s' % (market, codename, barchart_date_id)
            barchartdef = '%s%s' % (codename, barchart_date_id)

            return barchartdef
        except:
            raise ValueError("Can't turn %s %s into a Barchart Contract" % (self.instrument_code, self.contract_date))

    def get_barchartcode_for_instrument(self):

        return self._barchart_instrument_data.get_barchartcode_for_instrument(self.instrument_code)

    def get_barchartmarket_for_instrument(self):

        return self._barchart_instrument_data.get_barchartmarket_for_instrument(self.instrument_code)

    def get_start_date(self):

        return self._barchart_instrument_data.get_start_date(self.instrument_code)

    def get_dividing_factor(self):

        return self._barchart_instrument_data.get_barchart_dividing_factor(self.instrument_code)

class barchartFuturesContractPriceData(futuresContractPriceData):
    """
    Class to specifically get individual futures price data for barchart
    """

    def __init__(self):

        super().__init__()

        self.name = "simData connection for individual futures contracts prices, Barchart"

    def __repr__(self):
        return self.name

    def get_prices_for_contract_object(self, contract_object):
        """
        We do this because we have no way of checking if BARCHART has something without actually trying to get it
        """
        return self._get_prices_for_contract_object_no_checking(contract_object)

    def _get_prices_for_contract_object_no_checking(self, futures_contract_object):
        """

        :param futures_contract_object: futuresContract
        :return: futuresContractPrices
        """
        self.log.label(instrument_code=futures_contract_object.instrument_code,
                       contract_date=futures_contract_object.date[2:4])


        try:
            barchart_contract = _barchartFuturesContract(futures_contract_object)
        except:
            self.log.warning("Can't parse contract object to find the BARCHART identifier")
            return futuresContractPrices.create_empty()

        try:
            # contract_data = barchart.get(barchart_contract.barchart_identifier())
            contract_data=od.history(barchart_contract.barchart_identifier(), historical_type = 'daily')['results']
            contract_data=pd.DataFrame(contract_data)[['open', 'high', 'low', 'close', 'volume']]
            contract_data.tail()
        except Exception as exception:
            self.log.warn("Can't get BARCHART data for %s error %s" % (barchart_contract.barchart_identifier(), exception))
            return futuresContractPrices.create_empty()

        try:
            data = barchartFuturesContractPrices(contract_data)
        except:
            self.log.error(
                "Barchart API error: data fields are not as expected %s" % ",".join(list(contract_data.columns)))
            return futuresContractPrices.create_empty()

        # apply multiplier
        factor = barchart_contract.get_dividing_factor()
        data = data / factor

        return data

class barchartFuturesContractPrices(futuresContractPrices):
    """
    Parses Barchart format into our format

    Does any transformations needed to price etc
    """

    def __init__(self, contract_data):

        try:
            new_data = pd.DataFrame(dict(OPEN=contract_data.open,
                                         CLOSE=contract_data.close,
                                         HIGH=contract_data.high,
                                         LOW=contract_data.low,
                                         SETTLE=contract_data.volume))
        except AttributeError:
            try:
                new_data = pd.DataFrame(dict(OPEN=contract_data.OPEN,
                                             CLOSE=contract_data.CLOSE,
                                             HIGH=contract_data.HIGH,
                                             LOW=contract_data.LOW,
                                             OI=contract_data.OI,
                                             SYMBOL=contract_data.SYMBOL,
                                             TIMESTAMP=contract_data.TIMESTAMP,
                                             TRADINGDAY=contract_data.TRADINGDAY,
                                             VOLUME=contract_data.VOLUME))
            except AttributeError:
                try:
                    new_data = pd.DataFrame(dict(OPEN=contract_data.OPEN,
                                                 CLOSE=contract_data.CLOSE,
                                                 HIGH=contract_data.HIGH,
                                                 LOW=contract_data.LOW,
                                                 OI=contract_data.OI,
                                                 SYMBOL=contract_data.SYMBOL,
                                                 TIMESTAMP=contract_data.TIMESTAMP,
                                                 TRADINGDAY=contract_data.TRADINGDAY,
                                                 VOLUME=contract_data.VOLUME))
                except:
                    raise Exception(
                        "Barchart API error: data fields %s are not as expected" % ",".join(list(contract_data.columns)))

        super().__init__(new_data)
