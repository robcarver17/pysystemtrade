from sysdata.futures.rolls import rollParametersData
from sysobjects.rolls import rollParameters

from sysdata.mongodb.mongo_connection import (
    mongoConnection,
    MONGO_ID_KEY,
    mongo_clean_ints,
)
from syslogdiag.log import logtoscreen

ROLL_COLLECTION = "futures_roll_parameters"


class mongoRollParametersData(rollParametersData):
    """
    Read and write data class to get roll data


    """

    def __init__(
            self,
            mongo_db=None,
            log=logtoscreen("mongoRollParametersData")):

        super().__init__(log=log)

        self._mongo = mongoConnection(ROLL_COLLECTION, mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("instrument_code")

        self.name = (
            "simData connection for futures roll parameters, mongodb %s/%s @ %s -p %s " %
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

    def _get_roll_parameters_without_checking(self, instrument_code):

        result_dict = self._mongo.collection.find_one(
            dict(instrument_code=instrument_code)
        )
        result_dict.pop(MONGO_ID_KEY)
        result_dict.pop("instrument_code")

        roll_parameters_object = rollParameters.create_from_dict(result_dict)

        return roll_parameters_object

    def _delete_roll_parameters_data_without_any_warning_be_careful(
        self, instrument_code
    ):
        self._mongo.collection.remove(dict(instrument_code=instrument_code))
        self.log.terse("Deleted %s from %s" % (instrument_code, self.name))

    def _add_roll_parameters_without_checking_for_existing_entry(
        self, roll_parameters_object, instrument_code
    ):

        roll_parameters_object_dict = roll_parameters_object.as_dict()
        roll_parameters_object_dict["instrument_code"] = instrument_code
        cleaned_object_dict = mongo_clean_ints(roll_parameters_object_dict)
        self._mongo.collection.insert_one(cleaned_object_dict)
        self.log.terse("Added %s to %s" % (instrument_code, self.name))
