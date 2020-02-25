from pymongo import MongoClient, ASCENDING, IndexModel
from copy import copy
import numpy as np
import yaml

from syscore.fileutils import get_filename_for_package
from syscore.genutils import get_safe_from_dict
MONGO_CONFIG_FILE = get_filename_for_package('sysproduction.config.mongo_config.yaml')

LIST_OF_MONGO_PARAMS = ['db', 'host']

# CHANGE THESE IN THE PRIVATE CONFIG FILE, NOT HERE. SEE THE PRECEDENCE IN MONGO DEFAULTS
DEFAULT_MONGO_PARAMS = dict(db = 'production', host = 'localhost')

# DO NOT CHANGE THIS VALUE!!!! IT WILL SCREW UP ARCTIC
DEFAULT_MONGO_PORT = 27017

MONGO_ID_STR = '_id_'
MONGO_ID_KEY = '_id'

from syscore.fileutils import PRIVATE_CONFIG_FILE


def mongo_defaults(mongo_config_file = MONGO_CONFIG_FILE, private_config_file =PRIVATE_CONFIG_FILE, **kwargs):
    """
    Returns mongo configuration with following precedence

    1- if passed in arguments: db, host, port, data_map, collection_suffix - use that
    2- if defined in private_config file, use that. mongo_db, mongo_host, mongo_port,
    3- if defined in mongo_config file, use that.
    3- otherwise use defaults from DEFAULT_MONGO_SPECS

    :return: mongo db, hostname, port, data_map, collection_suffix
    """
    defaults_dict = DEFAULT_MONGO_PARAMS

    try:
        with open(mongo_config_file) as file_to_parse:
            yaml_dict_mongo_config = yaml.load(file_to_parse)
    except:
        yaml_dict_mongo_config={}

    try:
        with open(private_config_file) as file_to_parse:
            yaml_dict_private_config = yaml.load(file_to_parse)
    except:
        yaml_dict_private_config={}

    yaml_dict = {}
    for arg_name in LIST_OF_MONGO_PARAMS:
        yaml_arg_name = 'mongo_'+arg_name

        # Start with defaults
        arg_value = defaults_dict[arg_name]
        # Overwrite with mongo config
        arg_value = get_safe_from_dict(yaml_dict_mongo_config, arg_name, arg_value)
        # Overwrite with private config
        arg_value = get_safe_from_dict(yaml_dict_private_config, arg_name, arg_value)
        # Overwrite with kwargs
        arg_value = get_safe_from_dict(kwargs, arg_name, arg_value)

        # Write
        yaml_dict[arg_name] = arg_value

    # Get from dictionary
    mongo_db = yaml_dict['db']
    hostname = yaml_dict['host']
    port = DEFAULT_MONGO_PORT

    return mongo_db, hostname, port


class mongoDb(object):
    """
    Keeps track of mongo database we are connected to

    But requires adding a collection with mongoConnection before useful
    """

    def __init__(self,  **kwargs):

        database_name, host, port = mongo_defaults(**kwargs)

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


    def close(self):
        self.client.close()

    """
    Following two methods implement context manager
    """
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

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

def create_update_dict(mongo_record_dict):
    """
    Mongo needs $key names to do updates

    :param mongo_record_dict: dict
    :return: dict
    """

    new_dict = [("$%s" % key, value) for key,value in mongo_record_dict.items()]

    return new_dict