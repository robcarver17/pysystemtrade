"""
IB connection using ib-insync https://ib-insync.readthedocs.io/api.html

"""

import time

from ib_insync import IB

from sysbrokers.IB.ib_client import ibClient
from sysbrokers.IB.ib_connection_defaults import ib_defaults
from sysbrokers.IB.ib_server import ibServer
from syscore.objects import arg_not_supplied, missing_data

from syslogdiag.log import logtoscreen

from sysdata.private_config import get_private_then_default_key_value


def get_broker_account() -> str:

    account_id = get_private_then_default_key_value(
        "broker_account", raise_error=False
    )
    if account_id is missing_data:
        return arg_not_supplied
    else:
        return account_id


class connectionIB(ibClient, ibServer):
    """
    Connection object for connecting IB
    (A database plug in will need to be added for streaming prices)
    """

    def __init__(
        self,
        client_id: int,
        ipaddress=None,
        port=None,
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
        ipaddress, port, __ = ib_defaults(ipaddress=ipaddress, port=port)

        # The client id is pulled from a mongo database
        # If for example you want to use a different database you could do something like:
        # connectionIB(mongo_ib_tracker =
        # mongoIBclientIDtracker(database_name="another")

        # You can pass a client id yourself, or let IB find one

        # If you copy for another broker include this line
        log.label(broker="IB", clientid=client_id)
        self._ib_connection_config = dict(
            ipaddress=ipaddress, port=port, client=client_id)

        # if you copy for another broker, don't forget the logs
        ibServer.__init__(self, log=log)
        ibClient.__init__(self, log=log)

        ib = IB()

        account = get_broker_account()
        if account is missing_data:
            self.log.error("Broker account ID not found in private config - may cause issues")
            ib.connect(ipaddress, port, clientId=client_id, account=account)
        else:
            ib.connect(ipaddress, port, clientId=client_id, account=account)

        # Attempt to fix connection bug
        time.sleep(5)

        # Add handlers, from ibServer methods
        ib.errorEvent += self.error_handler

        self.ib = ib

    def __repr__(self):
        return "IB broker connection" + str(self._ib_connection_config)

    def client_id(self):
        return self._ib_connection_config["client"]

    def close_connection(self):
        self.log.msg("Terminating %s" % str(self._ib_connection_config))
        try:
            # Try and disconnect IB client
            self.ib.disconnect()
        except BaseException:
            self.log.warn(
                "Trying to disconnect IB client failed... ensure process is killed"
            )


