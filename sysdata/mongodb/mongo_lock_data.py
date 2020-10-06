from sysdata.production.locks import lockData, lock_off, lock_on
from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY
from syslogdiag.log import logtoscreen

LOCK_STATUS_COLLECTION = "locks"


class mongoLockData(lockData):
    """
    Read and write data class to get lock data


    """

    def __init__(self, mongo_db=None, log=logtoscreen("mongoLockData")):
        super().__init__(log=log)

        self._mongo = mongoConnection(
            LOCK_STATUS_COLLECTION, mongo_db=mongo_db)

        self._mongo.create_index("instrument_code")

        self.name = "Data connection for lock data, mongodb %s/%s @ %s -p %s " % (
            self._mongo.database_name,
            self._mongo.collection_name,
            self._mongo.host,
            self._mongo.port,
        )

    def __repr__(self):
        return self.name

    def get_lock_for_instrument(self, instrument_code):
        result = self._mongo.collection.find_one(
            dict(instrument_code=instrument_code))
        if result is None:
            return lock_off
        lock = result["lock"]

        return lock

    def add_lock_for_instrument(self, instrument_code):
        if self.is_instrument_locked(instrument_code):
            # already locked
            return None
        object_dict = dict(instrument_code=instrument_code, lock=lock_on)
        self._mongo.collection.insert_one(object_dict)

    def remove_lock_for_instrument(self, instrument_code):
        self._mongo.collection.remove(dict(instrument_code=instrument_code))

    def get_list_of_locked_instruments(self):

        cursor = self._mongo.collection.find()
        list_of_dicts = [dict for dict in cursor]
        _ = [db_entry.pop(MONGO_ID_KEY) for db_entry in list_of_dicts]
        output_list = [
            db_entry["instrument_code"]
            for db_entry in list_of_dicts
            if db_entry["lock"] == lock_on
        ]

        return output_list

    def _get_list_of_trade_limits_for_cursor(self, cursor):

        trade_limits = [(tradeLimit.from_dict(db_dict))
                        for db_dict in list_of_dicts]

        list_of_trade_limits = listOfTradeLimits(trade_limits)

        return list_of_trade_limits
