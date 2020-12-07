"""
IB connection using ib-insync https://ib-insync.readthedocs.io/api.html

"""

import time

from ib_insync import IB

from sysbrokers.IB.ib_client import ibClient
from sysdata.mongodb.mongo_IB_client_id import mongoIbClientIdData
from sysbrokers.IB.ib_server import ibServer
from syscore.genutils import get_safe_from_dict
from syscore.objects import arg_not_supplied, missing_data

from sysdata.private_config import get_list_of_private_then_default_key_values, get_private_then_default_key_value
from syslogdiag.log import logtoscreen

DEFAULT_IB_IPADDRESS = "127.0.0.1"
DEFAULT_IB_PORT = 4001
DEFAULT_IB_IDOFFSET = 1

LIST_OF_IB_PARAMS = ["ipaddress", "port", "idoffset"]


def ib_defaults(**kwargs):
    """
    Returns ib configuration with following precedence
    1- if passed in arguments: ipaddress, port, idoffset - use that
    2- if defined in private_config file, use that. ib_ipaddress, ib_port, ib_idoffset
    3 - if defined in system defaults file, use that
    4- otherwise use defaults DEFAULT_IB_IPADDRESS, DEFAULT_IB_PORT, DEFAULT_IB_IDOFFSET

    :return: mongo db, hostname, port
    """

    param_names_with_prefix = [
        "ib_" + arg_name for arg_name in LIST_OF_IB_PARAMS]
    config_dict = get_list_of_private_then_default_key_values(
        param_names_with_prefix)

    yaml_dict = {}
    for arg_name in LIST_OF_IB_PARAMS:
        yaml_arg_name = "ib_" + arg_name

        # Start with config (precedence: private config, then system config)
        arg_value = config_dict[yaml_arg_name]
        # Overwrite with kwargs
        arg_value = get_safe_from_dict(kwargs, arg_name, arg_value)

        # Write
        yaml_dict[arg_name] = arg_value

    # Get from dictionary
    ipaddress = yaml_dict.get("ipaddress", DEFAULT_IB_IPADDRESS)
    port = yaml_dict.get("port", DEFAULT_IB_PORT)
    idoffset = yaml_dict.get("idoffset", DEFAULT_IB_IDOFFSET)

    return ipaddress, port, idoffset

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

    def close_connection(self):
        self.log.msg("Terminating %s" % str(self._ib_connection_config))
        try:
            # Try and disconnect IB client
            self.ib.disconnect()
        except BaseException:
            self.log.warn(
                "Trying to disconnect IB client failed... ensure process is killed"
            )
        finally:
            self.db_id_tracker.release_clientid(
                self._ib_connection_config["client"])


