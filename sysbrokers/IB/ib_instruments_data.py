from sysbrokers.IB.config.ib_instrument_config import (
    IBconfig,
    read_ib_config_from_file,
    get_instrument_object_from_config,
    get_instrument_code_from_broker_code,
    IB_FUTURES_CONFIG_FILE,
    get_instrument_list_from_ib_config,
)
from sysbrokers.IB.ib_instruments import (
    futuresInstrumentWithIBConfigData,
)
from sysbrokers.IB.ib_connection import connectionIB
from sysbrokers.broker_instrument_data import brokerFuturesInstrumentData

from syscore.constants import arg_not_supplied

from sysdata.data_blob import dataBlob

from syslogdiag.log_to_screen import logtoscreen


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

    def get_instrument_code_from_broker_code(
        self,
        ib_code: str,
        ib_multiplier: float = arg_not_supplied,
        ib_exchange: str = arg_not_supplied,
    ) -> str:
        config = self.ib_config
        broker_code = get_instrument_code_from_broker_code(
            config=config,
            ib_code=ib_code,
            log=self.log,
            ib_multiplier=ib_multiplier,
            ib_exchange=ib_exchange,
        )

        return broker_code

    def _get_instrument_data_without_checking(self, instrument_code: str):
        return self.get_futures_instrument_object_with_IB_data(instrument_code)

    def get_futures_instrument_object_with_IB_data(
        self, instrument_code: str
    ) -> futuresInstrumentWithIBConfigData:

        config = self.ib_config
        instrument_object = get_instrument_object_from_config(
            instrument_code, log=self.log, config=config
        )

        return instrument_object

    def get_list_of_instruments(self) -> list:
        """
        Get instruments that have price data
        Pulls these in from a config file

        :return: list of str
        """

        config = self.ib_config
        instrument_list = get_instrument_list_from_ib_config(config, log=self.log)

        return instrument_list

    # Configuration read in and cache
    @property
    def ib_config(self) -> IBconfig:
        config = getattr(self, "_config", None)
        if config is None:
            config = self._get_and_set_ib_config_from_file()

        return config

    def _get_and_set_ib_config_from_file(self) -> IBconfig:

        config_data = read_ib_config_from_file(log=self.log)

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
