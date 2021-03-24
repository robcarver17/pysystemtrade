from pymongo import MongoClient, ASCENDING
from copy import copy
import numpy as np

from syscore.objects import arg_not_supplied
from sysdata.config.production_config import get_production_config

LIST_OF_MONGO_PARAMS = ["mongo_db", "mongo_host", "mongo_port"]


MONGO_INDEX_ID = "_id_"
MONGO_ID_KEY = "_id"

def mongo_defaults(**kwargs):
    """
    Returns mongo configuration with following precedence

    1- if passed in arguments: mongo_db, mongo_host, mongo_port - use that
    2- if defined in private_config file, use that. mongo_db, mongo_host, mongo_port
    3- if defined in system defaults file, use that: mongo_db, mongo_host

    :return: mongo db, hostname, port
    """
    # this will include defaults.yaml if not defined in private
    passed_param_names = list(kwargs.keys())
    production_config =get_production_config()
    output_dict = {}
    for param_name in LIST_OF_MONGO_PARAMS:

        if param_name in passed_param_names:
            param_value = kwargs[param_name]
        else:
            param_value = arg_not_supplied
            
        if param_value is arg_not_supplied:

            param_value = getattr(production_config, param_name)

        output_dict[param_name] = param_value

    # Get from dictionary
    mongo_db = output_dict["mongo_db"]
    hostname = output_dict["mongo_host"]
    port = output_dict["mongo_port"]

    return mongo_db, hostname, port


class MongoClientFactory(object):
    """
    Only one MongoClient is needed per Python process and MongoDB instance.

    I'm not sure why anyone would need more than one MongoDB instance,
    but it's easy to support, so why not?
    """

    def __init__(self):
        self.mongo_clients = {}

    def get_mongo_client(self, host, port):
        key = (host, port)
        if key in self.mongo_clients:
            return self.mongo_clients.get(key)
        else:
            client = MongoClient(host=host, port=port)
            self.mongo_clients[key] = client
            return client


# Only need one of these
mongo_client_factory = MongoClientFactory()


class mongoDb():
    """
    Keeps track of mongo database we are connected to

    But requires adding a collection with mongoConnection before useful
    """

    def __init__(self, mongo_database_name: str = arg_not_supplied,
                 mongo_host: str = arg_not_supplied,
                 mongo_port: int  = arg_not_supplied):

        database_name, host, port = mongo_defaults(mongo_db = mongo_database_name,
                                                   mongo_host = mongo_host,
                                                   mongo_port = mongo_port)

        self.database_name = database_name
        self.host = host
        self.port = port

        client = mongo_client_factory.get_mongo_client(host, port)
        db = client[database_name]

        self.client = client
        self.db = db

    def __repr__(self):
        return "Mongodb database: host %s, port %d, db name %s" % (
            self.host,
            self.port,
            self.database_name,
        )


class mongoConnection(object):
    """
    All of our mongo connections use this class (for static data, not time series which goes via arctic)

    """

    def __init__(self, collection_name: str, mongo_db: mongoDb=arg_not_supplied):

        # FIXME REMOVE NONE WHEN CODE PROPERLY REFACTORED
        if mongo_db is arg_not_supplied or mongo_db is None:
            mongo_db = mongoDb()

        database_name = mongo_db.database_name
        host = mongo_db.host
        port = mongo_db.port
        db = mongo_db.db
        client = mongo_db.client

        collection = db[collection_name]

        self.database_name = database_name
        self.collection_name = collection_name
        self.host = host
        self.port = port

        self.client = client
        self.db = db
        self.collection = collection

    def __repr__(self):
        return "Mongodb connection: host %s, port %d, db name %s, collection %s" % (
            self.host, self.port, self.database_name, self.collection_name, )

    def get_indexes(self):

        raw_index_information = copy(self.collection.index_information())

        if len(raw_index_information) == 0:
            return []

        # '__id__' is always in index if there is data
        raw_index_information.pop(MONGO_INDEX_ID)

        # mongo have buried this deep...
        index_keys = [index_entry["key"][0][0]
                      for index_entry in raw_index_information.values()]

        return index_keys

    def check_for_index(self, indexname):
        if indexname in self.get_indexes():
            return True
        else:
            return False

    def create_index(self, indexname, order=ASCENDING):
        if self.check_for_index(indexname):
            pass
        else:
            self.collection.create_index([(indexname, order)], unique=True)

    def create_multikey_index(
        self, indexname1, indexname2, order1=ASCENDING, order2=ASCENDING
    ):

        joint_indexname = indexname1 + "_" + indexname2
        if self.check_for_index(joint_indexname):
            pass
        else:
            self.collection.create_index(
                [(indexname1, order1), (indexname2, order2)],
                unique=True,
                name=joint_indexname,
            )

def mongo_clean_ints(dict_to_clean):
    """
    Mongo doesn't like ints

    :param dict_to_clean: dict
    :return: dict
    """
    new_dict = copy(dict_to_clean)
    for key_name in new_dict.keys():
        key_value = new_dict[key_name]
        if (isinstance(key_value, int)) or (isinstance(key_value, np.int64)):
            key_value = float(key_value)

        new_dict[key_name] = key_value

    return new_dict
