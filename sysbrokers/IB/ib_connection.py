"""
IB connection using ib-insync https://ib-insync.readthedocs.io/api.html

"""

import time

from ib_insync import IB

from sysbrokers.IB.ib_client import ibClient
from sysbrokers.IB.ib_server import ibServer
from syscore.genutils import get_safe_from_dict
from syscore.objects import arg_not_supplied, missing_data

from sysdata.private_config import get_list_of_private_then_default_key_values, get_private_then_default_key_value
from syslogdiag.log import logtoscreen
from sysdata.mongodb.mongo_connection import mongoConnection, mongoDb

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
        client=None,
        ipaddress=None,
        port=None,
        log=logtoscreen("connectionIB"),
        mongo_db=arg_not_supplied,
    ):
        """
        :param client: client id. If not passed then will get from database specified by mongo_db
        :param ipaddress: IP address of machine running IB Gateway or TWS. If not passed then will get from private config file, or defaults
        :param port: Port listened to by IB Gateway or TWS
        :param log: logging object
        :param mongo_db: mongoDB connection
        """

        # resolve defaults
        ipaddress, port, idoffset = ib_defaults(ipaddress=ipaddress, port=port)

        # The client id is pulled from a mongo database
        # If for example you want to use a different database you could do something like:
        # connectionIB(mongo_ib_tracker =
        # mongoIBclientIDtracker(database_name="another")

        # You can pass a client id yourself, or let IB find one

        self.db_id_tracker = mongoIBclientIDtracker(
            mongo_db=mongo_db, log=log, idoffset=idoffset
        )
        client = self.db_id_tracker.return_valid_client_id(client)

        # If you copy for another broker include this line
        log.label(broker="IB", clientid=client)
        self._ib_connection_config = dict(
            ipaddress=ipaddress, port=port, client=client)

        # if you copy for another broker, don't forget the logs
        ibServer.__init__(self, log=log)
        ibClient.__init__(self, log=log)

        ib = IB()

        account = get_broker_account()
        if account is missing_data:
            self.log.error("Broker account ID not found in private config - may cause issues")
            ib.connect(ipaddress, port, clientId=client, account=account)
        else:
            ib.connect(ipaddress, port, clientId=client, account=account)

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


IB_CLIENT_COLLECTION = "IBClientTracker"


class mongoIBclientIDtracker(object):
    """
    Read and write data class to get next used client id
    """

    def __init__(
        self,
        mongo_db=arg_not_supplied,
        idoffset=arg_not_supplied,
        log=logtoscreen("mongoIDTracker"),
    ):

        if mongo_db is arg_not_supplied:
            mongo_db = mongoDb()

        if idoffset is arg_not_supplied:
            _notused_ipaddress, _notused_port, idoffset = ib_defaults()

        self._mongo = mongoConnection(IB_CLIENT_COLLECTION, mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("client_id")

        self.name = "Tracking IB client IDs, mongodb %s/%s @ %s -p %s " % (
            self._mongo.database_name,
            self._mongo.collection_name,
            self._mongo.host,
            self._mongo.port,
        )

        self.log = log
        self._idoffset = idoffset

    def __repr__(self):
        return self.name

    def _is_clientid_used(self, clientid):
        """
        Checks if a clientis is in use
        :param clientid: int
        :return: bool
        """
        current_ids = self._get_list_of_clientids()
        if clientid in current_ids:
            return True
        else:
            return False

    def return_valid_client_id(self, clientid_to_try=None):
        """
        If clientid_to_try is None, return the next free ID
        If clientid_to_try is being used, return the next free ID, otherwise allow that to be used
        :param clientid_to_try: int or None
        :return: int
        """
        if clientid_to_try is None:
            clientid_to_use = self.get_next_clientid()

        elif self._is_clientid_used(clientid_to_try):
            # being used, get another one
            # this will also lock it
            clientid_to_use = self.get_next_clientid()
        else:
            # okay it's been passed, and we can use it. So let's lock and use
            # it
            clientid_to_use = clientid_to_try
            self._add_clientid(clientid_to_use)  # lock

        return clientid_to_use

    def get_next_clientid(self) -> int:
        """
        Returns a client id which will be locked so no other use can use it
        The clientid in question is the lowest available unused value
        :return: clientid
        """

        current_list_of_ids = self._get_list_of_clientids()
        next_id = get_next_id_from_current_list(current_list_of_ids, id_offset=self._idoffset)

        # lock
        self._add_clientid(next_id)

        return next_id

    def _get_list_of_clientids(self) -> list:
        cursor = self._mongo.collection.find()
        clientids = [db_entry["client_id"] for db_entry in cursor]

        return clientids

    def _add_clientid(self, next_id):
        self._mongo.collection.insert_one(dict(client_id=next_id))
        self.log.msg("Locked ID %d" % next_id)

    def clear_all_clientids(self):
        """
        Clear all the client ids
        Should be done daily
        :return:
        """
        self._mongo.collection.delete_many({})
        self.log.msg("Released all IDs")

    def release_clientid(self, clientid):
        """
        Delete a client id lock
        :param clientid:
        :return: None
        """

        self._mongo.collection.delete_one(dict(client_id=clientid))
        self.log.msg("Released ID %d" % clientid)

def get_next_id_from_current_list(current_list_of_ids: list, id_offset: int = 0) -> int:
    if len(current_list_of_ids) == 0:
        # no IDS in use
        return id_offset

    full_set_of_available_ids = set(
        range(id_offset, max(current_list_of_ids) + 1)
    )

    next_id = get_next_id_from_current_list_and_full_set(current_list_of_ids, full_set_of_available_ids)

    return next_id


def get_next_id_from_current_list_and_full_set(current_list_of_ids: list, full_set_of_available_ids: set) -> int:

    unused_values = full_set_of_available_ids - set(current_list_of_ids)
    if len(unused_values)==0:
        # no gaps, return the higest number plus 1
        return max(current_list_of_ids) + 1
    else:
        # there is a gap, use the lowest numbered one
        return min(unused_values)

