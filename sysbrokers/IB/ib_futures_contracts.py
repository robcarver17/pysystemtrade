import pandas as pd
from syscore.fileutils import get_filename_for_package
from syscore.genutils import value_or_npnan

from sysdata.futures.contracts import futuresContractData
from sysobjects.instruments import futuresInstrument
from sysobjects.contract_dates_and_expiries import expiryDate
from syslogdiag.log import logtoscreen
from syscore.objects import missing_contract, missing_instrument, missing_file
from sysbrokers.IB.ib_contracts import futuresInstrumentWithIBData, NOT_REQUIRED_FOR_IB, ibInstrumentData

IB_FUTURES_CONFIG_FILE = get_filename_for_package(
    "sysbrokers.IB.ib_config_futures.csv")


class ibFuturesContractData(futuresContractData):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This gets HISTORIC data from interactive brokers. It is blocking code
    In a live production system it is suitable for running on a daily basis to get end of day prices

    """

    def __init__(self, ibconnection, log=logtoscreen("ibFuturesContractData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB Futures per contract data %s" % str(self.ibconnection)

    def get_brokers_instrument_code(self, instrument_code):
        futures_instrument_with_ib_data = self.get_futures_instrument_object_with_IB_data(instrument_code)
        return futures_instrument_with_ib_data.broker_symbol

    def get_instrument_code_from_broker_code(self, ib_code):
        config = self._get_ib_config()
        config_row = config[config.IBSymbol == ib_code]
        if len(config_row) == 0:
            msg = "Broker symbol %s not found in configuration file!" % ib_code
            self.log.critical(msg)
            raise Exception(msg)

        if len(config_row) > 1:
            msg = (
                "Broker symbol %s appears more than once in configuration file!" %
                ib_code)
            self.log.critical(msg)
            raise Exception(msg)

        return config_row.iloc[0].Instrument

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

    def get_min_tick_size_for_contract(self, contract_object):
        new_log = self.log.setup(
            instrument_code=contract_object.instrument_code,
            contract_date=contract_object.date,
        )

        contract_object_with_ib_data = self.get_contract_object_with_IB_metadata(
            contract_object)
        if contract_object_with_ib_data is missing_contract:
            new_log.msg("Can't resolve contract so can't find tick size")
            return missing_contract

        min_tick_size = self.ibconnection.ib_get_min_tick_size(
            contract_object_with_ib_data
        )

        if min_tick_size is missing_contract:
            new_log.msg("No tick size found")
            return missing_contract

        return min_tick_size

    def get_trading_hours_for_contract(self, contract_object):
        """

        :param contract_object:
        :return: list of paired date times
        """
        new_log = self.log.setup(
            instrument_code=contract_object.instrument_code,
            contract_date=contract_object.date,
        )

        contract_object_with_ib_data = self.get_contract_object_with_IB_metadata(
            contract_object)
        if contract_object_with_ib_data is missing_contract:
            new_log.msg("Can't resolve contract so can't find expiry date")
            return missing_contract

        trading_hours = self.ibconnection.ib_get_trading_hours(
            contract_object_with_ib_data
        )

        if trading_hours is missing_contract:
            new_log.msg("No IB expiry date found")
            trading_hours = []

        return trading_hours

    def get_actual_expiry_date_for_contract(self, contract_object):
        """
        Get the actual expiry date of a contract from IB

        :param contract_object: type futuresContract
        :return: YYYYMMDD or None
        """
        new_log = self.log.setup(
            instrument_code=contract_object.instrument_code,
            contract_date=contract_object.date,
        )

        contract_object_with_ib_data = self.get_contract_object_with_IB_metadata(
            contract_object)
        if contract_object_with_ib_data is missing_contract:
            new_log.msg("Can't resolve contract so can't find expiry date")
            return missing_contract

        expiry_date = self.ibconnection.broker_get_contract_expiry_date(
            contract_object_with_ib_data
        )

        if expiry_date is missing_contract:
            new_log.msg("No IB expiry date found")
            return missing_contract
        else:
            expiry_date = expiryDate.from_str(
                expiry_date)

        return expiry_date

    def get_contract_object_with_IB_metadata(self, contract_object):

        futures_instrument_with_ib_data = self.get_futures_instrument_object_with_IB_data(
            contract_object.instrument_code
        )
        if futures_instrument_with_ib_data is missing_instrument:
            return missing_contract

        contract_object_with_ib_data = (
            contract_object.new_contract_with_replaced_instrument_object(
                futures_instrument_with_ib_data
            )
        )

        return contract_object_with_ib_data

    def get_futures_instrument_object_with_IB_data(self, instrument_code) ->futuresInstrumentWithIBData:
        new_log = self.log.setup(instrument_code=instrument_code)

        try:
            assert instrument_code in self.get_instruments_with_config_data()
        except BaseException:
            new_log.warn(
                "Instrument %s is not in IB configuration file" %
                instrument_code)
            return missing_instrument

        config = self._get_ib_config()
        if config is missing_file:
            new_log.warn(
                "Can't get config for instrument %s as IB configuration file missing" %
                instrument_code)
            return missing_instrument

        instrument_object = get_instrument_object_from_config(
            instrument_code, config=config
        )

        return instrument_object

    def get_instruments_with_config_data(self):
        """
        Get instruments that have price data
        Pulls these in from a config file

        :return: list of str
        """

        config = self._get_ib_config()
        if config is missing_file:
            self.log.warn(
                "Can't get list of instruments because IB config file missing"
            )
            return []

        instrument_list = list(config.Instrument)

        return instrument_list

    # Configuration read in and cache
    def _get_ib_config(self):
        config = getattr(self, "_config", None)
        if config is None:
            self._config = config = self._get_and_set_ib_config_from_file()

        return config

    def _get_and_set_ib_config_from_file(self):

        try:
            config_data = get_ib_config()
        except BaseException:
            self.log.warn("Can't read file %s" % IB_FUTURES_CONFIG_FILE)
            config_data = missing_file

        self._config = config_data

        return config_data

    def get_all_contract_objects_for_instrument_code(self, *args, **kwargs):
        raise NotImplementedError(
            "Consider implementing for consistent interface")

    def get_contract_object(self, *args, **kwargs):
        raise NotImplementedError(
            "Consider implementing for consistent interface")

    def delete_contract_data(self, *args, **kwargs):
        raise NotImplementedError("IB is ready only")

    def is_contract_in_data(self, *args, **kwargs):
        raise NotImplementedError(
            "Consider implementing for consistent interface")

    def add_contract_data(self, *args, **kwargs):
        raise NotImplementedError("IB is ready only")


def get_instrument_object_from_config(instrument_code: str, config=None) ->futuresInstrumentWithIBData:
    if config is None:
        config = get_ib_config()
    config_row = config[config.Instrument == instrument_code]
    symbol = config_row.IBSymbol.values[0]
    exchange = config_row.IBExchange.values[0]
    currency = value_or_npnan(config_row.IBCurrency.values[0], NOT_REQUIRED_FOR_IB)
    ib_multiplier = value_or_npnan(
        config_row.IBMultiplier.values[0], NOT_REQUIRED_FOR_IB)
    my_multiplier = value_or_npnan(
        config_row.MyMultiplier.values[0], 1.0)
    ignore_weekly = config_row.IgnoreWeekly.values[0]

    # We use the flexibility of futuresInstrument to add additional arguments
    instrument = futuresInstrument(instrument_code)
    ib_data = ibInstrumentData(symbol, exchange, currency=currency,
        ibMultiplier=ib_multiplier,
        myMultiplier=my_multiplier,
        ignoreWeekly=ignore_weekly
        )

    futures_instrument_with_ib_data = futuresInstrumentWithIBData(instrument, ib_data)

    return futures_instrument_with_ib_data


def get_ib_config():
    return pd.read_csv(IB_FUTURES_CONFIG_FILE)
