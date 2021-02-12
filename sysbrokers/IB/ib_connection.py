"""
IB connection using ib-insync https://ib-insync.readthedocs.io/api.html

"""

import time

from ib_insync import IB

from sysbrokers.IB.ib_connection_defaults import ib_defaults
from syscore.objects import missing_data,arg_not_supplied

from syslogdiag.log import logtoscreen

from sysdata.config.private_config import get_private_config


def get_broker_account() -> str:
    config = get_private_config()
    account_id = config.get_element_or_missing_data(
        "broker_account")
    if account_id is missing_data:
        return missing_data
    else:
        return account_id

class connectionIB(object):
    """
    Connection object for connecting IB
    (A database plug in will need to be added for streaming prices)
    """

    def __init__(
        self,
        client_id: int,
        ipaddress: str=arg_not_supplied,
        port: int=arg_not_supplied,
        log=logtoscreen("connectionIB")
    ):
        """
        :param client_id: client id
        :param ipaddress: IP address of machine running IB Gateway or TWS. If not passed then will get from private config file, or defaults
        :param port: Port listened to by IB Gateway or TWS
        :param log: logging object
        :param mongo_db: mongoDB connection
        """

        # resolve defaults

        ipaddress, port, __ = ib_defaults(ib_ipaddress=ipaddress, ib_port=port)

        # The client id is pulled from a mongo database
        # If for example you want to use a different database you could do something like:
        # connectionIB(mongo_ib_tracker =
        # mongoIBclientIDtracker(database_name="another")

        # You can pass a client id yourself, or let IB find one

        # If you copy for another broker include this line
        log.label(broker="IB", clientid=client_id)
        self._ib_connection_config = dict(
            ipaddress=ipaddress, port=port, client=client_id)

        ib = IB()

        account = get_broker_account()

        if account is missing_data:
            self.log.error("Broker account ID not found in private config - may cause issues")
            ib.connect(ipaddress, port, clientId=client_id)
        else:
            ib.connect(ipaddress, port, clientId=client_id, account=account)

        # Sometimes takes a few seconds to resolve... only have to do this once per process so no biggie
        time.sleep(5)

        self._ib = ib
        self._log = log
        self._account = account

    @property
    def ib(self):
        return self._ib

    @property
    def log(self):
        return self._log

    def __repr__(self):
        return "IB broker connection" + str(self._ib_connection_config)

    def client_id(self):
        return self._ib_connection_config["client"]

    @property
    def account(self):
        return self._account

    def close_connection(self):
        self.log.msg("Terminating %s" % str(self._ib_connection_config))
        try:
            # Try and disconnect IB client
            self.ib.disconnect()
        except BaseException:
            self.log.warn(
                "Trying to disconnect IB client failed... ensure process is killed"
            )


