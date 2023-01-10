from dateutil.tz import tz
import datetime

from ib_insync import Contract
from ib_insync import IB

from sysbrokers.IB.ib_connection import connectionIB

from syscore.dateutils import strip_timezone_fromdatetime
from syslogdiag.logger import logger
from syslogdiag.log_to_screen import logtoscreen

# IB state that pacing violations only occur for bar sizes of less than 1 minute
# See footnote at bottom of
# https://interactivebrokers.github.io/tws-api/historical_limitations.html#pacing_violations
PACING_INTERVAL_SECONDS = 0.5


STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY = 600

IB_ERROR_TYPES = {200: "invalid_contract"}
IB_IS_ERROR = [200]


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
            contract_str = ""
        else:
            contract_str = " (%s/%s)" % (
                contract.symbol,
                contract.lastTradeDateOrContractMonth,
            )

        msg = "Reqid %d: %d %s %s" % (reqid, error_code, error_string, contract_str)

        iserror = error_code in IB_IS_ERROR
        if iserror:
            # Serious requires some action
            myerror_type = IB_ERROR_TYPES.get(error_code, "generic")
            self.broker_error(msg, myerror_type)

        else:
            # just a warning / general message
            self.broker_message(msg)

    def broker_error(self, msg, myerror_type):
        self.log.warn(msg)

    def broker_message(self, msg):
        self.log.msg(msg)

    def refresh(self):
        self.ib.sleep(0.00001)
