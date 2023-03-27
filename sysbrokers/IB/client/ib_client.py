import datetime
from typing import Union, List
from ib_insync import IB

from sysbrokers.IB.ib_connection import connectionIB
from sysbrokers.IB.ib_contracts import ibContract, ibContractDetails
from sysbrokers.IB.config.ib_instrument_config import (
    IBconfig,
    read_ib_config_from_file,
    get_instrument_code_from_broker_instrument_identity,
    IBInstrumentIdentity,
)

from syscore.constants import arg_not_supplied
from syscore.cache import Cache
from syscore.exceptions import missingContract

from syslogdiag.pst_logger import pst_logger
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
        self, ibconnection: connectionIB, log: pst_logger = logtoscreen("ibClient")
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
        self._cache = Cache(self)

    @property
    def cache(self) -> Cache:
        return self._cache

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
        self, reqid: int, error_code: int, error_string: str, contract: ibContract
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

        msg = "Reqid %d: %d %s" % (reqid, error_code, error_string)

        log_to_use = self._get_log_for_contract(contract)

        iserror = error_code in IB_IS_ERROR
        if iserror:
            # Serious requires some action
            myerror_type = IB_ERROR_TYPES.get(error_code, "generic")
            self.broker_error(msg=msg, myerror_type=myerror_type, log=log_to_use)

        else:
            # just a general message
            self.broker_message(msg=msg, log=log_to_use)

    def _get_log_for_contract(self, contract: ibContract) -> pst_logger:
        if contract is None:
            log_to_use = self.log.setup()
        else:
            ib_expiry_str = contract.lastTradeDateOrContractMonth
            instrument_code = self.get_instrument_code_from_broker_contract_object(
                contract
            )
            futures_contract = futuresContract(instrument_code, ib_expiry_str)
            log_to_use = futures_contract.specific_log(self.log)

        return log_to_use

    def broker_error(self, msg, log, myerror_type):
        log.warn(msg)

    def broker_message(self, log, msg):
        log.msg(msg)

    def refresh(self):
        self.ib.sleep(0.00001)

    def get_instrument_code_from_broker_contract_object(
        self, broker_contract_object: ibContract
    ) -> str:

        broker_identity = self.broker_identity_for_contract(broker_contract_object)
        instrument_code = self.get_instrument_code_from_broker_identity_for_contract(
            broker_identity
        )

        return instrument_code

    def get_instrument_code_from_broker_identity_for_contract(
        self, ib_instrument_identity: IBInstrumentIdentity, config=arg_not_supplied
    ) -> str:
        if config is arg_not_supplied:
            config = self.ib_config

        instrument_code = get_instrument_code_from_broker_instrument_identity(
            ib_instrument_identity=ib_instrument_identity,
            log=self.log,
            config=config,
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

    def broker_identity_for_contract(
        self,
        ib_contract_pattern: ibContract,
    ) -> IBInstrumentIdentity:

        contract_details = self.get_contract_details(
            ib_contract_pattern=ib_contract_pattern,
            allow_expired=False,
            allow_multiple_contracts=False,
        )

        return IBInstrumentIdentity(
            ib_code=str(contract_details.contract.symbol),
            ib_multiplier=float(contract_details.contract.multiplier),
            ib_exchange=str(contract_details.contract.exchange),
        )

    def get_contract_details(
        self,
        ib_contract_pattern: ibContract,
        allow_expired: bool = False,
        allow_multiple_contracts: bool = False,
    ) -> Union[ibContractDetails, List[ibContractDetails]]:

        """CACHING HERE CAUSES TOO MANY ERRORS SO DON'T USE IT"""
        contract_details = self._get_contract_details(
            ib_contract_pattern, allow_expired=allow_expired
        )

        if len(contract_details) == 0:
            raise missingContract

        if allow_multiple_contracts:
            return contract_details

        elif len(contract_details) > 1:
            self.log.critical("Multiple contracts and only expected one")

        return contract_details[0]

    def _get_contract_details(
        self, ib_contract_pattern: ibContract, allow_expired: bool = False
    ) -> List[ibContractDetails]:
        ## in case of caching
        ib_contract_pattern.includeExpired = allow_expired

        return self.ib.reqContractDetails(ib_contract_pattern)
