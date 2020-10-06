from sysdata.production.roll_state_storage import rollStateData, no_state_available
from syscore.objects import success
from sysdata.mongodb.mongo_connection import (
    mongoConnection,
    MONGO_ID_KEY,
    mongo_clean_ints,
)
from syslogdiag.log import logtoscreen

ROLL_STATUS_COLLECTION = "futures_roll_status"


class mongoRollStateData(rollStateData):
    """
    Read and write data class to get roll state data


    """

    def __init__(self, mongo_db=None, log=logtoscreen("mongoRollStateData")):

        super().__init__(log=log)

        self._mongo = mongoConnection(
            ROLL_STATUS_COLLECTION, mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("instrument_code")

        self.name = (
            "Data connection for futures roll state, mongodb %s/%s @ %s -p %s "
            % (
                self._mongo.database_name,
                self._mongo.collection_name,
                self._mongo.host,
                self._mongo.port,
            )
        )

    def __repr__(self):
        return self.name

    def get_list_of_instruments(self):
        cursor = self._mongo.collection.find()
        codes = [db_entry["instrument_code"] for db_entry in cursor]

        return codes

    def _get_roll_state_no_default(self, instrument_code):
        result_dict = self._mongo.collection.find_one(
            dict(instrument_code=instrument_code)
        )
        if result_dict is None:
            return no_state_available
        result_dict.pop(MONGO_ID_KEY)
        result_dict.pop("instrument_code")

        roll_status = result_dict["roll_state"]

        return roll_status

    def _set_roll_state_without_checking(
            self, instrument_code, new_roll_state):
        find_object_dict = dict(instrument_code=instrument_code)
        new_values_dict = {"$set": {"roll_state": new_roll_state}}
        self._mongo.collection.update_one(
            find_object_dict, new_values_dict, upsert=True
        )
        self.log.terse(
            "Updated roll state of %s to %s in %s"
            % (instrument_code, new_roll_state, self.name)
        )

        return success
