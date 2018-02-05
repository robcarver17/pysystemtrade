from sysdata.futures.instruments import futuresInstrumentData, futuresInstrument
from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY, mongo_clean_ints
from copy import copy

INSTRUMENT_COLLECTION = 'futures_instruments'
DEFAULT_DB = 'production'

class mongoFuturesInstrumentData(futuresInstrumentData):
    """
    Read and write data class to get instrument data

    We'd inherit from this class for a specific implementation

    """

    def __init__(self, database_name = DEFAULT_DB):

        super().__init__()

        self._mongo = mongoConnection(database_name, INSTRUMENT_COLLECTION)

        # this won't create the index if it already exists
        self._mongo.create_index("instrument_code")

        self.name = "Data connection for futures instruments, mongodb %s/%s @ %s -p %s " % (
            self._mongo.database_name, self._mongo.collection_name, self._mongo.host, self._mongo.port)

    def __repr__(self):
        return self.name

    def get_list_of_instruments(self):
        cursor = self._mongo.collection.find()
        codes = [db_entry['instrument_code'] for db_entry in cursor]

        return codes

    def _get_instrument_data_without_checking(self, instrument_code):

        result_dict = self._mongo.collection.find_one(dict(instrument_code=instrument_code))
        result_dict.pop(MONGO_ID_KEY)

        instrument_object = futuresInstrument.create_from_dict(result_dict)

        return instrument_object

    def _delete_instrument_data_without_any_warning_be_careful(self, instrument_code):
        self._mongo.collection.remove(dict(instrument_code = instrument_code))
        self.log.terse("Deleted %s from %s" % (instrument_code, self.name))

    def _add_instrument_data_without_checking_for_existing_entry(self, instrument_object):
        instrument_object_dict = instrument_object.as_dict()
        cleaned_object_dict = mongo_clean_ints(instrument_object_dict)
        self._mongo.collection.insert_one(cleaned_object_dict)
        self.log.terse("Added %s to %s" % (instrument_object.instrument_code, self.name))


