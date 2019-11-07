"""
Classes to create instances of connections

Connections contain plugs to data and brokers, so the two can talk to each other
"""

import yaml
from threading import Thread

from sysbrokers.IB.ibClient import ibClient
from sysbrokers.IB.ibServer import ibServer
from syslogdiag.log import logtoscreen
from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY

from syscore.fileutils import get_filename_for_package

PRIVATE_CONFIG_FILE = get_filename_for_package("private.private_config.yaml")

DEFAULT_IB_IPADDRESS='127.0.0.1'
DEFAULT_IB_PORT = 4001
DEFAULT_IB_IDOFFSET = 1

def ib_defaults(config_file =PRIVATE_CONFIG_FILE, **kwargs):
    """
    Returns ib configuration with following precedence

    1- if passed in arguments: ipaddress, port, idoffset - use that
    2- if defined in private_config file, use that. ib_ipaddress, ib_port, ib_idoffset
    3- otherwise use defaults DEFAULT_MONGO_DB, DEFAULT_MONGO_HOST, DEFAULT_MONGOT_PORT

    :return: mongo db, hostname, port
    """

    try:
        with open(config_file) as file_to_parse:
            yaml_dict = yaml.load(file_to_parse)
    except:
        yaml_dict={}

    # Overwrite with passed arguments - these will take precedence over values in config file
    for arg_name in ['ipaddress', 'port', 'idoffset']:
        arg_value = kwargs.get(arg_name, None)
        if arg_value is not None:
            yaml_dict['ib_'+arg_name] = arg_value

    # Get from dictionary
    ipaddress = yaml_dict.get('ib_ipaddress', DEFAULT_IB_IPADDRESS)
    port = yaml_dict.get('ib_port', DEFAULT_IB_PORT)
    idoffset = yaml_dict.get('ib_idoffset', DEFAULT_IB_IDOFFSET)

    return ipaddress, port, idoffset



class connectionIB(ibClient, ibServer):
    """
    Connection object for connecting IB
    (A database plug in will need to be added for streaming prices)
    """

    def __init__(self, client=None, ipaddress=None, port=None, log=logtoscreen("connectionIB"),
                 mongo_db=None):

        """

        :param client: client id. If not passed then will get from database specified by db_id_tracker
        :param ipaddress: IP address of machine running IB Gateway or TWS. If not passed then will get from private config file, or defaults
        :param port: Port listened to by IB Gateway or TWS
        :param log: logging object
        :param db_id_tracker: Eithier none (to use the default or an object that quacks like class mongoIBclientIDtracker)
        """

        # resolve defaults
        ipaddress, port, idoffset = ib_defaults(ipaddress=ipaddress, port=port)

        # If you copy for another broker include this line
        log.label(broker="IB", clientid = client)
        self._ib_connection_config = dict(ipaddress = ipaddress, port = port, client = client)

        # You can pass a client id yourself, or let IB find one
        if client is None:
            # The client id is pulled from a mongo database
            # If for example you want to use a different database you could do something like:
            # connectionIB(mongo_ib_tracker = mongoIBclientIDtracker(database_name="another")
            #

            db_id_tracker = mongoIBclientIDtracker(mongo_db = mongo_db, log=log, idoffset=idoffset)

            # get and lock a client id
            client = db_id_tracker.get_next_clientid()
            # client IDs are not released; assume we clean them daily

        # IB specific - this is to ensure we don't get reqID conflicts between different processes
        reqIDoffset = client*1000

        #if you copy for another broker, don't forget the logs
        ibServer.__init__(self, log=log)
        ibClient.__init__(self, wrapper = self, reqIDoffset=reqIDoffset, log=log)

        # if you copy for another broker, don't forget to do this
        self.broker_init_error()

        # this is all very IB specific
        self.connect(ipaddress, port, client)
        thread = Thread(target = self.run)
        thread.start()
        setattr(self, "_thread", thread)

    def __repr__(self):
        return "IB broker connection"+str(self._ib_connection_config)


IB_CLIENT_COLLECTION = 'IBClientTracker'


class mongoIBclientIDtracker(object):
    """
    Read and write data class to get next used client id


    """

    def __init__(self, mongo_db=None, idoffset=None, log=logtoscreen("mongoIDTracker")):

        if idoffset is None:
            _notused_ipaddress, _notused_port, idoffset = ib_defaults()

        self._mongo = mongoConnection(IB_CLIENT_COLLECTION, mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("client_id")

        self.name = "Tracking IB client IDs, mongodb %s/%s @ %s -p %s " % (
            self._mongo.database_name, self._mongo.collection_name, self._mongo.host, self._mongo.port)

        self.log = log
        self._idoffset = idoffset

    def __repr__(self):
        return self.name

    def get_next_clientid(self):
        """
        Returns a client id which will be locked so no other use can use it

        The clientid in question is the lowest available unused value

        :return: clientid
        """

        current_list = self._get_list_of_clientids()
        if len(current_list)==0:
            next_id = self._idoffset
        else:
            full_set = set(range(0, max(current_list) + 2)) # includes next value up in case no space
            missing_values = full_set - set(current_list)
            next_id = min(missing_values)

        # lock
        self._add_clientid(next_id)

        return next_id

    def _get_list_of_clientids(self):
        cursor = self._mongo.collection.find()
        clientids = [db_entry['client_id'] for db_entry in cursor]

        return clientids

    def _add_clientid(self, next_id):
        self._mongo.collection.insert_one(dict(client_id=next_id))
        self.log.msg("Locked ID %d" %  next_id)

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
        self.log.msg("Released ID %d" %  clientid)
