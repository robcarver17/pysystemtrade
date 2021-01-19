from dateutil.tz import tz
import datetime
import pandas as pd
from copy import copy

from ib_insync import util, ComboLeg, Contract
from ib_insync import IB, Trade



from sysobjects.contracts import futuresContract

from syscore.objects import missing_contract, arg_not_supplied, missing_order, missing_data

from syscore.dateutils import adjust_timestamp_to_include_notional_close_and_time_offset, strip_timezone_fromdatetime
from syslogdiag.log import logtoscreen, logger



from sysbrokers.IB.ib_translate_broker_order_objects import tradeWithContract, listOfTradesWithContracts
from sysbrokers.IB.ib_contracts import (
    resolve_multiple_expiries,
    ibcontractWithLegs)
from sysbrokers.IB.ib_instruments import ib_futures_instrument_just_symbol, futuresInstrumentWithIBConfigData, \
    ib_futures_instrument
from sysbrokers.IB.ib_positions import (
    from_ib_positions_to_dict,
    resolveBS,
    resolveBS_for_list,
positionsFromIB
)


_PACING_PERIOD_SECONDS = 10 * 60
_PACING_PERIOD_LIMIT = 60
PACING_INTERVAL_SECONDS = 1 + (_PACING_PERIOD_SECONDS / _PACING_PERIOD_LIMIT)


STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY = 600

IB_ERROR_TYPES = {200: "invalid_contract"}
IB_IS_ERROR = [200]

def from_ibcontract_to_tuple(ibcontract):
    return (ibcontract.symbol, ibcontract.lastTradeDateOrContractMonth)


class ibClient(object):
    """
    Client specific to interactive brokers

    Overrides the methods in the base class specifically for IB

    """

    def __init__(self, ib:IB, log=logtoscreen("ibClient")):

        # means our first call won't be throttled for pacing
        self.last_historic_price_calltime = (
            datetime.datetime.now() -
            datetime.timedelta(
                seconds=_PACING_PERIOD_SECONDS))
        self._ib = ib
        self._contract_register = dict()
        self._log = log

    @property
    def ib(self) -> IB:
        return self._ib

    @property
    def log(self):
        return self._log

    @property
    def contract_register(self):
        return self.contract_register

    def add_contract_to_register(self, ibcontract, log_tags={}):
        """
        The contract register is used to map IB contracts back to instrument and contractid
        This makes logging cleaner

        :param ibcontract: an IB contract tuple (
        :param log_tags: dict of keywords that will pass to log
        :return:
        """
        contract_register = self.contract_register
        contract_tuple = from_ibcontract_to_tuple(ibcontract)
        contract_register[contract_tuple] = log_tags


    def get_contract_log_tags_from_register(self, ibcontract):
        """
         The contract register is used to map IB contracts back to instrument and contractid
        This makes logging cleaner

        :param contract: IB contract
        :return: log_tags, dict
        """
        if ibcontract is None:
            return {}
        contract_register = self.contract_register
        contract_tuple = from_ibcontract_to_tuple(ibcontract)
        log_tags = contract_register.get(contract_tuple, {})

        return log_tags

    def error_handler(self, reqid, error_code, error_string, contract):
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

        msg = "Reqid %d: %d %s %s" % (
            reqid, error_code, error_string, contract_str)

        # Associate a contract with tags eg my instrument and contract id
        log_tags = self.get_contract_log_tags_from_register(contract)

        iserror = error_code in IB_IS_ERROR
        if iserror:
            # Serious requires some action
            myerror_type = IB_ERROR_TYPES.get(error_code, "generic")
            self.broker_error(msg, myerror_type, log_tags)

        else:
            # just a warning / general message
            self.broker_message(msg, log_tags)


    def broker_error(self, msg, myerror_type, log_tags):
        self.log.warn(msg, **log_tags)

    def broker_message(self, msg, log_tags):
        self.log.msg(msg, **log_tags)

    def refresh(self):
        self.ib.sleep(0.00001)


    def get_broker_time_local_tz(self):
        ib_time = self.ib.reqCurrentTime()
        local_ib_time_with_tz = ib_time.astimezone(tz.tzlocal())
        local_ib_time = strip_timezone_fromdatetime(local_ib_time_with_tz)

        return local_ib_time



