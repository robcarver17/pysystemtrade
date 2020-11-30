from sysdata.production.process_control import controlProcessData, controlProcess
from syscore.objects import success, missing_data
from sysdata.mongodb.mongo_connection import (
    mongoConnection,
    MONGO_ID_KEY,
    mongo_clean_ints,
)
from syslogdiag.log import logtoscreen

PROCESS_CONTROL_COLLECTION = "process_control"


class mongoControlProcessData(controlProcessData):
    """
    Read and write data class to get process control data


    """

    def __init__(
            self,
            mongo_db=None,
            log=logtoscreen("mongoControlProcessData")):

        super().__init__(log=log)

        self._mongo = mongoConnection(
            PROCESS_CONTROL_COLLECTION, mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("process_name")

        self.name = "Data connection for process control, mongodb %s/%s @ %s -p %s " % (
            self._mongo.database_name,
            self._mongo.collection_name,
            self._mongo.host,
            self._mongo.port,
        )

    def __repr__(self):
        return self.name

    def get_list_of_process_names(self):
        cursor = self._mongo.collection.find()
        codes = [db_entry["process_name"] for db_entry in cursor]

        return codes

    def _get_control_for_process_name_without_default(self, process_name):
        result_dict = self._mongo.collection.find_one(
            dict(process_name=process_name))
        if result_dict is None:
            return missing_data
        result_dict.pop(MONGO_ID_KEY)
        result_dict.pop("process_name")

        control_object = controlProcess.from_dict(result_dict)

        return control_object

    def _modify_existing_control_for_process_name(
        self, process_name, new_control_object
    ):
        find_object_dict = dict(process_name=process_name)
        new_values_dict = {"$set": new_control_object.as_dict()}
        self._mongo.collection.update_one(
            find_object_dict, new_values_dict, upsert=True
        )

    def _add_control_for_process_name(self, process_name, new_control_object):
        object_dict = new_control_object.as_dict()
        object_dict["process_name"] = process_name
        self._mongo.collection.insert_one(object_dict)
