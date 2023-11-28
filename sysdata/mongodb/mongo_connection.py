from pymongo import MongoClient, ASCENDING
from copy import copy
import numpy as np
import re

from syscore.constants import arg_not_supplied
from sysdata.config.production_config import get_production_config

LIST_OF_MONGO_PARAMS = ["mongo_db", "mongo_host", "mongo_port"]


MONGO_INDEX_ID = "_id_"
MONGO_ID_KEY = "_id"

# regular expression pattern for mongodb connection URLs
host_pattern = re.compile("^(mongodb://)([^:]+):([^@]+)@([^/]+)")


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
    production_config = get_production_config()
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


class mongoDb:
    """
    Keeps track of mongo database we are connected to

    But requires adding a collection with mongoConnection before useful
    """

    def __init__(
        self,
        mongo_database_name: str = arg_not_supplied,
        mongo_host: str = arg_not_supplied,
        mongo_port: int = arg_not_supplied,
    ):
        database_name, host, port = mongo_defaults(
            mongo_database_name=mongo_database_name,
            mongo_host=mongo_host,
            mongo_port=mongo_port,
        )

        self.database_name = database_name
        self.host = host
        self.port = port

        client = mongo_client_factory.get_mongo_client(host, port)
        db = client[database_name]

        self.client = client
        self.db = db

    def __repr__(self):
        clean_host = clean_mongo_host(self.host)
        return "Mongodb database: host %s, db name %s" % (
            clean_host,
            self.database_name,
        )


class mongoConnection(object):
    """
    All of our mongo connections use this class (for static data, not time series which goes via arctic)

    """

    def __init__(self, collection_name: str, mongo_db: mongoDb = arg_not_supplied):
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
        clean_host = clean_mongo_host(self.host)
        return "Mongodb connection: host %s, db name %s, collection %s" % (
            clean_host,
            self.database_name,
            self.collection_name,
        )

    def get_indexes(self):
        raw_index_information = copy(self.collection.index_information())

        if len(raw_index_information) == 0:
            return []

        # '__id__' is always in index if there is data
        raw_index_information.pop(MONGO_INDEX_ID)

        index_count = len(raw_index_information)
        index_names = []
        index_keys = []

        for k, v in raw_index_information.items():
            index_names.append(k)
            for key in v["key"]:
                index_keys.append(key[0])

        return index_count, index_names, index_keys

    def create_index(self, indexname, order=ASCENDING):
        index_count, index_names, index_keys = self.get_indexes()
        if indexname in index_keys:
            # we don't try to create a single key index if the key field is already used
            # in another index
            pass
        else:
            self.collection.create_index([(indexname, order)], unique=True)

    def create_compound_index(self, index_config: dict):
        name_parts = []
        key_tuples = []
        keys = index_config.pop("keys")
        for key, value in keys.items():
            name_parts.append(str(key))
            name_parts.append(str(value))
            key_tuples.append((key, value))
        new_index_name = "_".join(name_parts)

        index_count, index_names, index_keys = self.get_indexes()
        if index_count > 1 or len(index_keys) > 1 or new_index_name in index_names:
            # We don't try to create a compound index if:
            # - EITHER there is more than one index defined (likely created outside
            #     of PST)
            # - OR there is already some other compound index (likely created outside
            #     of PST)
            # - OR the name of an existing index matches what we would be about to
            #     create (we probably already made it)
            pass
        else:
            self.collection.create_index(
                key_tuples, name=new_index_name, **index_config
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


def clean_mongo_host(host_string):
    """
    If the host string is a mongodb connection URL with authentication values, then return just the host and port part
    :param host_string
    :return: host and port only
    """

    clean_host = host_string
    match = host_pattern.match(host_string)
    if match is not None:
        clean_host = match.group(4)

    return clean_host
