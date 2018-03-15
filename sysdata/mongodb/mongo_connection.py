from pymongo import MongoClient, ASCENDING, IndexModel
from copy import copy
import numpy as np

DEFAULT_DB = 'production'
DEFAULT_MONGO_HOST = 'localhost'
DEFAULT_MONGO_PORT = 27017
MONGO_ID_STR = '_id_'
MONGO_ID_KEY = '_id'

class mongoConnection(object):
    """
    All of our mongo connections use this class (for static data, not time series which goes via artic)

    """
    def __init__(self, database_name, collection_name, host = DEFAULT_MONGO_HOST, port = DEFAULT_MONGO_PORT):

        if database_name is None:
            database_name = DEFAULT_DB

        client = MongoClient(host=host, port=port)
        db = client[database_name]
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
               self.host, self.port, self.database_name, self.collection_name

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