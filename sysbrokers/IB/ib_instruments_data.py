import pandas as pd

from sysbrokers.IB.ib_instruments import (
    NOT_REQUIRED_FOR_IB,
    ibInstrumentConfigData,
    futuresInstrumentWithIBConfigData,
)
from sysbrokers.IB.ib_connection import connectionIB
from sysbrokers.broker_instrument_data import brokerFuturesInstrumentData
from sysdata.data_blob import dataBlob
from syscore.fileutils import resolve_path_and_filename_for_package
from syscore.genutils import return_another_value_if_nan
from syscore.constants import missing_instrument, missing_file

from sysobjects.instruments import futuresInstrument

from syslogdiag.log_to_screen import logtoscreen

IB_FUTURES_CONFIG_FILE = resolve_path_and_filename_for_package(
    "sysbrokers.IB.ib_config_futures.csv"
)


class IBconfig(pd.DataFrame):
    pass


def read_ib_config_from_file() -> IBconfig:
    df = pd.read_csv(IB_FUTURES_CONFIG_FILE)
    return IBconfig(df)


class ibFuturesInstrumentData(brokerFuturesInstrumentData):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This gets HISTORIC data from interactive brokers. It is blocking code
    In a live production system it is suitable for running on a daily basis to get end of day prices

    """

    def __init__(
        self,
        ibconnection: connectionIB,
        data: dataBlob,
        log=logtoscreen("ibFuturesContractData"),
    ):
        super().__init__(log=log, data=data)
        self._ibconnection = ibconnection

    def __repr__(self):
        return "IB Futures per contract data %s" % str(self.ibconnection)

    @property
    def ibconnection(self) -> connectionIB:
        return self._ibconnection

    def get_brokers_instrument_code(self, instrument_code: str) -> str:
        futures_instrument_with_ib_data = (
            self.get_futures_instrument_object_with_IB_data(instrument_code)
        )
        if futures_instrument_with_ib_data is missing_instrument:
            return missing_instrument
        return futures_instrument_with_ib_data.broker_symbol

    def get_instrument_code_from_broker_code(self, ib_code: str) -> str:
        config = self._get_ib_config()
        config_row = config[config.IBSymbol == ib_code]
        if len(config_row) == 0:
            msg = "Broker symbol %s not found in configuration file!" % ib_code
            self.log.critical(msg)
            raise Exception(msg)

        if len(config_row) > 1:
            ## need to resolve with multiplier
            instrument_code = self.get_instrument_code_from_broker_code_with_multiplier(
                ib_code
            )
        else:
            instrument_code = config_row.iloc[0].Instrument

        return instrument_code

    def get_instrument_code_from_broker_code_with_multiplier(self, ib_code: str) -> str:

        # FIXME PATCH
        if ib_code == "EOE":
            return "AEX"
        else:
            msg = (
                "Broker symbol %s appears more than once in configuration file and NOT AEX!!"
                % ib_code
            )
            self.log.critical(msg)
            raise Exception(msg)
        """
        this code will work but need to get multiplier from somewhere

        config = self._get_ib_config()
        config_rows = config[config.IBSymbol == ib_code]

        config_row = config_rows[config.IBMultiplier == multiplier]
        if len(config_row) > 1:

            msg = (
                "Broker symbol %s appears more than once in configuration file!"
                % ib_code
            )
            self.log.critical(msg)
            raise Exception(msg)

        return config_row.iloc[0].Instrument
        """

    def _get_instrument_data_without_checking(self, instrument_code: str):
        return self.get_futures_instrument_object_with_IB_data(instrument_code)

    def get_futures_instrument_object_with_IB_data(
        self, instrument_code: str
    ) -> futuresInstrumentWithIBConfigData:
        new_log = self.log.setup(instrument_code=instrument_code)

        try:
            assert instrument_code in self.get_list_of_instruments()
        except:
            new_log.warn(
                "Instrument %s is not in IB configuration file" % instrument_code
            )
            return missing_instrument

        config = self._get_ib_config()
        if config is missing_file:
            new_log.warn(
                "Can't get config for instrument %s as IB configuration file missing"
                % instrument_code
            )
            return missing_instrument

        instrument_object = get_instrument_object_from_config(
            instrument_code, config=config
        )

        return instrument_object

    def get_list_of_instruments(self) -> list:
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
    def _get_ib_config(self) -> IBconfig:
        config = getattr(self, "_config", None)
        if config is None:
            config = self._get_and_set_ib_config_from_file()

        return config

    def _get_and_set_ib_config_from_file(self) -> IBconfig:

        try:
            config_data = read_ib_config_from_file()
        except BaseException:
            self.log.warn("Can't read file %s" % IB_FUTURES_CONFIG_FILE)
            config_data = missing_file

        self._config = config_data

        return config_data

    def _delete_instrument_data_without_any_warning_be_careful(
        self, instrument_code: str
    ):
        raise NotImplementedError(
            "IB instrument config is read only - manually edit .csv file %s"
            % IB_FUTURES_CONFIG_FILE
        )

    def _add_instrument_data_without_checking_for_existing_entry(
        self, instrument_object
    ):
        raise NotImplementedError(
            "IB instrument config is read only - manually edit .csv file %s"
            % IB_FUTURES_CONFIG_FILE
        )


def get_instrument_object_from_config(
    instrument_code: str, config: IBconfig = None
) -> futuresInstrumentWithIBConfigData:
    if config is None:
        config = read_ib_config_from_file()

    config_row = config[config.Instrument == instrument_code]
    symbol = config_row.IBSymbol.values[0]
    exchange = config_row.IBExchange.values[0]
    currency = return_another_value_if_nan(
        config_row.IBCurrency.values[0], NOT_REQUIRED_FOR_IB
    )
    ib_multiplier = return_another_value_if_nan(
        config_row.IBMultiplier.values[0], NOT_REQUIRED_FOR_IB
    )
    price_magnifier = return_another_value_if_nan(
        config_row.priceMagnifier.values[0], 1.0
    )
    ignore_weekly = config_row.IgnoreWeekly.values[0]

    # We use the flexibility of futuresInstrument to add additional arguments
    instrument = futuresInstrument(instrument_code)
    ib_data = ibInstrumentConfigData(
        symbol,
        exchange,
        currency=currency,
        ibMultiplier=ib_multiplier,
        priceMagnifier=price_magnifier,
        ignoreWeekly=ignore_weekly,
    )

    futures_instrument_with_ib_data = futuresInstrumentWithIBConfigData(
        instrument, ib_data
    )

    return futures_instrument_with_ib_data
