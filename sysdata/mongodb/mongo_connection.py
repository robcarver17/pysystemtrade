from pymongo import MongoClient, ASCENDING, IndexModel
from copy import copy
import numpy as np
import yaml

from syscore.fileutils import get_filename_for_package

# CHANGE THESE IN THE PRIVATE CONFIG FILE, NOT HERE
DEFAULT_MONGO_DB = 'production'
DEFAULT_MONGO_HOST = 'localhost'

# DO NOT CHANGE THIS VALUE!!!! IT WILL SCREW UP ARCTIC
DEFAULT_MONGO_PORT = 27017

MONGO_ID_STR = '_id_'
MONGO_ID_KEY = '_id'

PRIVATE_CONFIG_FILE = get_filename_for_package("private.private_config.yaml")

def mongo_defaults(config_file =PRIVATE_CONFIG_FILE, **kwargs):
    """
    Returns mongo configuration with following precedence

    1- if passed in arguments: db, host, port - use that
    2- if defined in private_config file, use that. mongo_db, mongo_host, mongo_port
    3- otherwise use defaults DEFAULT_MONGO_DB, DEFAULT_MONGO_HOST, DEFAULT_MONGOT_PORT

    :return: mongo db, hostname, port
    """

    try:
        with open(config_file) as file_to_parse:
            yaml_dict = yaml.load(file_to_parse)
    except:
        yaml_dict={}

    # Overwrite with passed arguments - these will take precedence over values in config file
    for arg_name in ['db', 'host']:
        arg_value = kwargs.get(arg_name, None)
        if arg_value is not None:
            yaml_dict['mongo_'+arg_name] = arg_value

    # Get from dictionary
    mongo_db = yaml_dict.get('mongo_db', DEFAULT_MONGO_DB)
    hostname = yaml_dict.get('mongo_host', DEFAULT_MONGO_HOST)
    port = DEFAULT_MONGO_PORT

    return mongo_db, hostname, port


class mongoDb(object):
    """
    Keeps track of mongo database we are connected to

    But requires adding a collection with mongoConnection before useful
    """

    def __init__(self,  database_name = None, host = None):

        database_name, host, port = mongo_defaults(db=database_name, host=host)

        self.database_name = database_name
        self.host = host
        self.port = port

        client = MongoClient(host=host, port=port)
        db = client[database_name]

        self.client=client
        self.db=db

    def __repr__(self):
        return "Mongodb database: host %s, port %d, db name %s" % \
               (self.host, self.port, self.database_name)


class mongoConnection(object):
    """
    All of our mongo connections use this class (for static data, not time series which goes via artic)

    """
    def __init__(self,  collection_name, mongo_db = None):

        if mongo_db is None:
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

    def close(self):
        self.client.close()

    def __repr__(self):
        return "Mongodb connection: host %s, port %d, db name %s, collection %s" % \
               (self.host, self.port, self.database_name, self.collection_name)

    def get_indexes(self):

        raw_index_information = copy(self.collection.index_information())

        if len(raw_index_information)==0:
            return []

        ## '__id__' is always in index if there is data
        raw_index_information.pop(MONGO_ID_STR)

        ## mongo have buried this deep...
        index_keys = [index_entry['key'][0][0] for index_entry in raw_index_information.values()]

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
            self.collection.create_index([(indexname, order)],    unique = True)

    def create_multikey_index(self, indexname1, indexname2, order1=ASCENDING, order2=ASCENDING):

        joint_indexname = indexname1+"_"+indexname2
        if self.check_for_index(joint_indexname):
            pass
        else:
            self.collection.create_index([(indexname1, order1), (indexname2, order2)],
                                unique=True,
                                name = joint_indexname)

def mongo_clean_ints(dict_to_clean):
    """
    Mongo doesn't like ints

    :param dict_to_clean: dict
    :return: dict
    """
    new_dict = copy(dict_to_clean)
    for key_name in new_dict.keys():
        key_value = new_dict[key_name]
        if (type(key_value) is int) or (type(key_value) is np.int64):
            key_value = float(key_value)

        new_dict[key_name] = key_value

    return new_dict