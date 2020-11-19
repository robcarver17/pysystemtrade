import pandas as pd
from arctic import Arctic
from sysdata.mongodb.mongo_connection import mongoDb

"""
IMPORTANT NOTE: Make sure you have a mongodb running eg mongod --dbpath /home/yourusername/pysystemtrade/data/futures/arctic

This connection won't fail if mongo missing, but will hang

"""


class articConnection(object):
    """
    All of our ARCTIC mongo connections use this class (not static data which goes directly via mongo DB)

    """

    def __init__(self, collection_name, mongo_db=None):

        if mongo_db is None:
            mongo_db = mongoDb()

        database_name = mongo_db.database_name
        host = mongo_db.host

        # Arctic doesn't accept a port

        store = Arctic(host)
        library_name = database_name + "." + collection_name
        # will this fail if already exists??
        store.initialize_library(library_name)
        library = store[library_name]

        self.database_name = database_name
        self.collection_name = collection_name
        self.host = host

        self.store = store
        self.library_name = library_name
        self.library = library

    def __repr__(self):
        return "Arctic connection: host %s, db name %s, collection %s" % (
            self.host,
            self.database_name,
            self.collection_name,
        )

    def read(self, ident) -> pd.DataFrame:
        item = self.library.read(ident)
        return pd.DataFrame(item.data)

    def write(self, ident: str, data: pd.DataFrame):
        self.library.write(ident, data)

    def get_keynames(self) -> list:
        return self.library.list_symbols()

    def delete(self, ident: str):
        self.library.delete(ident)