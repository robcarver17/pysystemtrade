import datetime

from ib_insync import Contract
from ib_insync import IB

from sysbrokers.IB.ib_connection import connectionIB
from sysbrokers.IB.config.ib_instrument_config import (
    IBconfig,
    read_ib_config_from_file,
    get_instrument_code_from_broker_code,
)

from syslogdiag.logger import logger
from syslogdiag.log_to_screen import logtoscreen

from sysobjects.contracts import futuresContract

# IB state that pacing violations only occur for bar sizes of less than 1 minute
# See footnote at bottom of
# https://interactivebrokers.github.io/tws-api/historical_limitations.html#pacing_violations
PACING_INTERVAL_SECONDS = 0.5


STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY = 600

IB_ERROR_TYPES = {
    200: "ambgious_contract",
    501: "already connected",
    502: "can't connect",
    503: "TWS need upgrading",
    100: "Max messages exceeded",
    102: "Duplicate ticker",
    103: "Duplicate orderid",
    104: "can't modify filled order",
    105: "trying to modify different order",
    106: "can't transmit orderid",
    107: "can't transmit incomplete order",
    109: "price out of range",
    110: "tick size wrong for price",
    122: "No request tag has been found for order",
    123: "invalid conid",
    133: "submit order failed",
    134: "modify order failed",
    135: "cant find order",
    136: "order cant be cancelled",
    140: "size should be an integer",
    141: "price should be a double",
    201: "order rejected",
    202: "order cancelled",
}

IB_IS_ERROR = list(IB_ERROR_TYPES.keys())


class ibClient(object):
    """
    Client specific to interactive brokers

    We inherit from this to do interesting stuff, so this base class just offers error handling and get time

    """

    def __init__(
        self, ibconnection: connectionIB, log: logger = logtoscreen("ibClient")
    ):

        # means our first call won't be throttled for pacing
        self.last_historic_price_calltime = (
            datetime.datetime.now()
            - datetime.timedelta(seconds=PACING_INTERVAL_SECONDS)
        )

        # Add error handler
        ibconnection.ib.errorEvent += self.error_handler

        self._ib_connnection = ibconnection
        self._log = log

    @property
    def ib_connection(self) -> connectionIB:
        return self._ib_connnection

    @property
    def ib(self) -> IB:
        return self.ib_connection.ib

    @property
    def client_id(self) -> int:
        return self.ib.client.clientId

    @property
    def log(self):
        return self._log

    def error_handler(
        self, reqid: int, error_code: int, error_string: str, contract: Contract
    ):
        """
        Error handler called from server
        Needs to be attached to ib connection

        :param reqid: IB reqid
        :param error_code: IB error code
        :param error_string: IB error string
        :param contract: IB contract or None
        :return: success
        """
        if contract is None:
            ib_contract_str = ""
            log_to_use = self.log.setup()
        else:
            ib_instrument_code = contract.symbol
            ib_expiry_str = (contract.lastTradeDateOrContractMonth,)
            ib_contract_str = str("%s %s" % (ib_instrument_code, ib_expiry_str))

            instrument_code = self.get_instrument_code_from_broker_code(
                ib_instrument_code
            )

            futures_contract = futuresContract(instrument_code, ib_expiry_str)
            log_to_use = futures_contract.specific_log(self.log)

        msg = "Reqid %d: %d %s %s" % (reqid, error_code, error_string, ib_contract_str)

        iserror = error_code in IB_IS_ERROR
        if iserror:
            # Serious requires some action
            myerror_type = IB_ERROR_TYPES.get(error_code, "generic")
            self.broker_error(msg=msg, myerror_type=myerror_type, log=log_to_use)

        else:
            # just a general message
            self.broker_message(msg=msg, log=log_to_use)

    def broker_error(self, msg, log, myerror_type):
        log.warn(msg)

    def broker_message(self, log, msg):
        log.msg(msg)

    def refresh(self):
        self.ib.sleep(0.00001)

    def get_instrument_code_from_broker_code(self, ib_code: str) -> str:
        instrument_code = get_instrument_code_from_broker_code(
            log=self.log, ib_code=ib_code, config=self.ib_config
        )
        return instrument_code

    @property
    def ib_config(self) -> IBconfig:
        config = getattr(self, "_config", None)
        if config is None:
            config = self._get_and_set_ib_config_from_file()

        return config

    def _get_and_set_ib_config_from_file(self) -> IBconfig:

        config_data = read_ib_config_from_file(log=self.log)

        return config_data
