import pandas as pd
from arctic import Arctic
from sysdata.mongodb.mongo_connection import mongoDb, clean_mongo_host

"""
IMPORTANT NOTE: Make sure you have a mongodb running eg mongod --dbpath /home/yourusername/pysystemtrade/data/futures/arctic

This connection won't fail if mongo missing, but will hang

"""


class arcticData(object):
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

        self.database_name = database_name
        self.collection_name = collection_name
        self.host = host

        self.store = store
        self.library = self._setup_lib(store, database_name, collection_name)

    def __repr__(self):
        return (
            f"Arctic connection: host {clean_mongo_host(self.host)}, "
            f"db {self.database_name}, collection {self.collection_name}"
        )

    def read(self, ident) -> pd.DataFrame:
        item = self.library.read(ident)
        return pd.DataFrame(item.data)

    def write(self, ident: str, data: pd.DataFrame):
        self.library.write(ident, data)

    def get_keynames(self) -> list:
        return self.library.list_symbols()

    def has_keyname(self, keyname) -> bool:
        return self.library.has_symbol(keyname)

    def delete(self, ident: str):
        self.library.delete(ident)

    def _setup_lib(self, store: Arctic, db_name, coll_name):
        lib_name = db_name + "." + coll_name
        if lib_name not in store.list_libraries():
            store.initialize_library(lib_name)
        return store[lib_name]
