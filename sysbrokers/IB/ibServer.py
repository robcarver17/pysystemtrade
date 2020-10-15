"""
Handlers used by https://ib-insync.readthedocs.io/api.html flavour

"""

from syslogdiag.log import logtoscreen
from syscore.objects import success

# List of IB error codes that are blacklisted eg serious and require action
IB_IS_ERROR = [200]

# For each IB error code, map to one of my error types
# Useful for deciding which process should handle it
IB_ERROR_TYPES = {200: "invalid_contract"}


def from_ibcontract_to_tuple(ibcontract):
    return (ibcontract.symbol, ibcontract.lastTradeDateOrContractMonth)


class ibServer(object):
    def __init__(self, log=logtoscreen("ibServer")):
        self._contract_register = dict()
        self.log = log

    def add_contract_to_register(self, ibcontract, log_tags={}):
        """
        The contract register is used to map IB contracts back to instrument and contractid
        This makes logging cleaner

        :param ibcontract: an IB contract tuple (
        :param log_tags: dict of keywords that will pass to log
        :return:
        """
        contract_register = self._contract_register
        contract_tuple = from_ibcontract_to_tuple(ibcontract)
        contract_register[contract_tuple] = log_tags

        return success

    def get_contract_log_tags_from_register(self, ibcontract):
        """
         The contract register is used to map IB contracts back to instrument and contractid
        This makes logging cleaner

        :param contract: IB contract
        :return: log_tags, dict
        """
        if ibcontract is None:
            return {}
        contract_register = self._contract_register
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

        return success

    def broker_error(self, msg, myerror_type, log_tags):
        self.log.warn(msg, **log_tags)

    def broker_message(self, msg, log_tags):
        self.log.msg(msg, **log_tags)