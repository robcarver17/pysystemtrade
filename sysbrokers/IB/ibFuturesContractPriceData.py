
import pandas as pd
import datetime
from syscore.fileutils import get_filename_for_package
from syscore.genutils import value_or_npnan, NOT_REQUIRED


from sysdata.futures.futures_per_contract_prices import futuresContractPriceData, futuresContractPrices
from sysdata.futures.contracts import futuresContract, listOfFuturesContracts
from sysdata.futures.instruments import futuresInstrument
from sysdata.futures.contract_dates_and_expiries import expiryDate
from syslogdiag.log import logtoscreen
from syscore.objects import missing_contract, missing_instrument, missing_file

IB_FUTURES_CONFIG_FILE = get_filename_for_package("sysbrokers.IB.ibConfigFutures.csv")




class ibFuturesContractPriceData(futuresContractPriceData):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This gets HISTORIC data from interactive brokers. It is blocking code
    In a live production system it is suitable for running on a daily basis to get end of day prices

    """

    def __init__(self, ibconnection, log=logtoscreen("ibFuturesContractPriceData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB Futures per contract price data %s" % str(self.ibconnection)

    def has_data_for_contract(self, contract_object):
        """
        Does IB have data for a given contract?

        Overriden because we will have a problem matching expiry dates to nominal yyyymm dates
        :param contract_object:
        :return: bool
        """

        expiry_date = self.get_actual_expiry_date_for_contract(contract_object)
        if expiry_date is missing_contract:
            return False
        else:
            return True

    def get_instruments_with_price_data(self):
        """
        Get instruments that have price data
        Pulls these in from a config file

        :return: list of str
        """

        config = self._get_ib_config()
        if config is missing_file:
            self.log.warn("Can't get list of instruments because IB config file missing")
            return []

        instrument_list = list(config.Instrument)

        return instrument_list

    def contracts_with_price_data_for_instrument_code(self, instrument_code):
        """
        Valid contracts for a given instrument code

        :param instrument_code: str
        :return: list of contracts
        """
        new_log = self.log.setup(instrument_code=instrument_code)

        instrument_object_with_ib_config = self._get_instrument_object_with_IB_metadata(instrument_code)
        if instrument_object_with_ib_config is missing_instrument:
            new_log.warn("Can't get list of contracts for illdefined instrument %s" % instrument_code, instrument_code=instrument_code)
            return listOfFuturesContracts([])

        list_of_contract_dates = self.ibconnection.broker_get_futures_contract_list(instrument_object_with_ib_config)
        list_of_contracts = [futuresContract(instrument_code, contract_date)
                             for contract_date in list_of_contract_dates]

        return listOfFuturesContracts(list_of_contracts)

    def get_actual_expiry_date_for_contract(self, contract_object):
        """
        Get the actual expiry date of a contract from IB

        :param contract_object: type futuresContract
        :return: YYYYMMDD or None
        """
        new_log = self.log.setup(instrument_code=contract_object.instrument_code, contract_date=contract_object.date)

        contract_object_with_ib_data = self._get_contract_object_with_IB_metadata(contract_object)
        if contract_object_with_ib_data is missing_contract:
            new_log.msg("Can't resolve contract so can't find expiry date")
            return missing_contract

        expiry_date = self.ibconnection.broker_get_contract_expiry_date(contract_object_with_ib_data)

        if expiry_date is missing_contract:
            new_log.msg("No IB expiry date found")
        else:
            expiry_date = expiryDate.from_str(expiry_date, date_format="%Y%m%d")

        return expiry_date


    def get_prices_for_contract_object(self, contract_object):
        """
        Get some prices
        (daily frequency: using IB historical data)

        :param contract_object:  futuresContract
        :return: data
        """
        new_log = self.log.setup(instrument_code=contract_object.instrument_code, contract_date=contract_object.date)

        contract_object_with_ib_data = self._get_contract_object_with_IB_metadata(contract_object)
        if contract_object_with_ib_data is missing_contract:
            new_log.warn("Can't get data for %s" % str(contract_object))
            return futuresContractPrices.create_empty()

        price_data = self.ibconnection.broker_get_historical_futures_data_for_contract(contract_object_with_ib_data,
                                                                                       bar_freq = "D")

        if len(price_data)==0:
            new_log.msg("No IB price data found for %s" % str(contract_object))
            data = futuresContractPrices.create_empty()
        else:
            data = futuresContractPrices(price_data)

        data = futuresContractPrices(data[data.index<datetime.datetime.now()])
        data = data.remove_zero_volumes()

        return data

    def get_prices_at_frequency_for_contract_object(self, contract_object, freq="D"):
        """
        Get historical prices at a particular frequency

        We override this method, rather than _get_prices_at_frequency_for_contract_object_no_checking
        Because the list of dates returned by contracts_with_price_data is likely to not match (expiries)

        :param contract_object:  futuresContract
        :param freq: str; one of D, H, 15M, 5M, M, 10S, S
        :return: data
        """
        new_log = self.log.setup(instrument_code=contract_object.instrument_code, contract_date=contract_object.date)

        contract_object_with_ib_data = self._get_contract_object_with_IB_metadata(contract_object)
        if contract_object_with_ib_data is missing_contract:
            new_log.warn("Can't get data for %s" % str(contract_object))
            return futuresContractPrices.create_empty()

        price_data = self.ibconnection.broker_get_historical_futures_data_for_contract(contract_object_with_ib_data,
                                                                                       bar_freq = freq)

        if len(price_data)==0:
            new_log.warn("No IB price data found for %s" % str(contract_object))
            data = futuresContractPrices.create_empty()
        else:
            data = futuresContractPrices(price_data)

        data = futuresContractPrices(data[data.index<datetime.datetime.now()])
        data = data.remove_zero_volumes()

        return data



    def _get_contract_object_with_IB_metadata(self, contract_object):

        new_instrument_object = self._get_instrument_object_with_IB_metadata(contract_object.instrument_code)
        if new_instrument_object is missing_instrument:
            return missing_contract

        contract_object_with_ib_data = \
            contract_object.new_contract_with_replaced_instrument_object( new_instrument_object)

        return contract_object_with_ib_data

    def _get_instrument_object_with_IB_metadata(self, instrument_code):
        new_log = self.log.setup(instrument_code=instrument_code)

        try:
            assert instrument_code in self.get_instruments_with_price_data()
        except:
            new_log.warn("Instrument %s is not in IB configuration file" % instrument_code)
            return missing_instrument

        config = self._get_ib_config()
        if config is missing_file:
            new_log.warn("Can't get config for instrument %s as IB configuration file missing" % instrument_code)
            return missing_instrument

        instrument_object = get_instrument_object_from_config( instrument_code, config=config)

        return instrument_object

    # Configuration read in and cache
    def _get_ib_config(self):
        config = getattr(self, "_config", None)
        if config is None:
            config = self._get_and_set_ib_config_from_file()

        return config

    def _get_and_set_ib_config_from_file(self):

        try:
            config_data=get_ib_config()
        except:
            self.log.warn("Can't read file %s" % IB_FUTURES_CONFIG_FILE)
            config_data = missing_file

        self._config = config_data

        return config_data


    def _get_prices_for_contract_object_no_checking(self, *args, **kwargs):
        raise NotImplementedError("_get_prices_for_contract_object_no_checking should not be called for IB type object")

    def _get_prices_at_frequency_for_contract_object_no_checking(self, *args, **kwargs):
        raise NotImplementedError("_get_prices_at_frequency_for_contract_object_no_checking should not be called for IB type object")

    def _write_prices_for_contract_object_no_checking(self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def delete_prices_for_contract_object(self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def get_contracts_with_price_data(self, *args, **kwargs):
        raise NotImplementedError("Do not use get_contracts_with_price_data with IB")



def get_instrument_object_from_config( instrument_code, config = None):
    if config is None:
        config = get_ib_config()
    config_row = config[config.Instrument == instrument_code]
    symbol = config_row.IBSymbol.values[0]
    exchange = config_row.IBExchange.values[0]
    currency = value_or_npnan(config_row.IBCurrency.values[0], NOT_REQUIRED)
    ib_multiplier = value_or_npnan(config_row.IBMultiplier.values[0], NOT_REQUIRED)
    my_multiplier = value_or_npnan(config_row.MyMultiplier.values[0], NOT_REQUIRED)
    ignore_weekly = config_row.IgnoreWeekly.values[0]

    ## We use the flexibility of futuresInstrument to add additional arguments
    instrument_config = futuresInstrument(instrument_code, symbol=symbol, exchange=exchange, currency=currency,
                                          ibMultiplier=ib_multiplier, myMultiplier=my_multiplier,
                                          ignoreWeekly=ignore_weekly)

    return instrument_config

def get_ib_config():
    return pd.read_csv(IB_FUTURES_CONFIG_FILE)