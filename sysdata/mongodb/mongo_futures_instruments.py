import pandas as pd

from sysdata.futures.instruments import futuresInstrumentData, futuresInstrument
from sysdata.mongodb.mongo_connection import (
    mongoConnection,
    MONGO_ID_KEY,
    mongo_clean_ints,
)
from syslogdiag.log import logtoscreen

INSTRUMENT_COLLECTION = "futures_instruments"


class mongoFuturesInstrumentData(futuresInstrumentData):
    """
    Read and write data class to get instrument data

    We'd inherit from this class for a specific implementation

    """

    def __init__(self, mongo_db=None, log=logtoscreen(
            "mongoFuturesInstrumentData")):

        super().__init__(log=log)
        self._mongo = mongoConnection(INSTRUMENT_COLLECTION, mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("instrument_code")

        self.name = (
            "simData connection for futures instruments, mongodb %s/%s @ %s -p %s " %
            (self._mongo.database_name,
             self._mongo.collection_name,
             self._mongo.host,
             self._mongo.port,
             ))

    def __repr__(self):
        return self.name

    def get_list_of_instruments(self):
        cursor = self._mongo.collection.find()
        codes = [db_entry["instrument_code"] for db_entry in cursor]

        return codes

    def get_all_instrument_data(self):
        """
        Gets information about all instruments

        Returns dataframe of meta data, indexed by instrument code

        :return: pd.DataFrame
        """

        all_instrument_codes = self.get_list_of_instruments()
        all_instrument_objects = [
            self.get_instrument_data(instrument_code)
            for instrument_code in all_instrument_codes
        ]

        meta_data_keys = [
            instrument_object.meta_data.keys()
            for instrument_object in all_instrument_objects
        ]
        meta_data_keys_flattened = [
            item for sublist in meta_data_keys for item in sublist
        ]
        meta_data_keys_unique = list(set(meta_data_keys_flattened))

        meta_data_as_lists = dict(
            [
                (
                    metadata_name,
                    [
                        instrument_object.meta_data[metadata_name]
                        for instrument_object in all_instrument_objects
                    ],
                )
                for metadata_name in meta_data_keys_unique
            ]
        )

        meta_data_as_dataframe = pd.DataFrame(
            meta_data_as_lists, index=all_instrument_codes
        )

        return meta_data_as_dataframe

    def _get_instrument_data_without_checking(self, instrument_code):

        result_dict = self._mongo.collection.find_one(
            dict(instrument_code=instrument_code)
        )
        result_dict.pop(MONGO_ID_KEY)

        instrument_object = futuresInstrument.create_from_dict(result_dict)

        return instrument_object

    def _delete_instrument_data_without_any_warning_be_careful(
            self, instrument_code):
        self._mongo.collection.remove(dict(instrument_code=instrument_code))
        self.log.terse("Deleted %s from %s" % (instrument_code, self.name))

    def _add_instrument_data_without_checking_for_existing_entry(
        self, instrument_object
    ):
        instrument_object_dict = instrument_object.as_dict()
        cleaned_object_dict = mongo_clean_ints(instrument_object_dict)
        self._mongo.collection.insert_one(cleaned_object_dict)
        self.log.terse(
            "Added %s to %s" % (instrument_object.instrument_code, self.name)
        )
