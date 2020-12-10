from sysdata.production.generic_timed_storage import listOfEntriesData, classStrWithListOfEntriesAsListOfDicts
from sysdata.mongodb.mongo_connection import (
    mongoConnection,
    MONGO_ID_KEY
)
from syslogdiag.log import logtoscreen
from syscore.objects import success, missing_data
from copy import copy


class mongoListOfEntriesData(listOfEntriesData):
    """
    Read and write data class to get capital for each strategy


    """

    def _collection_name(self):
        raise NotImplementedError("Need to inherit for a specific data type")

    def _data_name(self):
        raise NotImplementedError("Need to inherit for a specific data type")

    def __init__(self, mongo_db=None, log=logtoscreen("mongoCapitalData")):

        super().__init__(log=log)

        self._mongo = mongoConnection(
            self._collection_name(), mongo_db=mongo_db)

        # this won't create the index if it already exists

        self.name = "Data connection for %s, mongodb %s/%s @ %s -p %s " % (
            self._data_name(),
            self._mongo.database_name,
            self._mongo.collection_name,
            self._mongo.host,
            self._mongo.port,
        )

    def __repr__(self):
        return self.name

    def _get_list_of_args_dict(self):
        cursor = self._mongo.collection.find()
        args_dict_list = [db_entry for db_entry in cursor]

        return args_dict_list

    def _get_series_dict_with_data_class_for_args_dict(self, args_dict: dict) ->classStrWithListOfEntriesAsListOfDicts:

        result_dict = self._mongo.collection.find_one(args_dict)
        if result_dict is None:
            return missing_data

        result_dict.pop(MONGO_ID_KEY)
        data_class = result_dict["data_class"]
        series_as_list_of_dicts = result_dict["entry_series"]

        class_str_with_series_as_list_of_dicts = \
            classStrWithListOfEntriesAsListOfDicts(data_class, series_as_list_of_dicts)

        return class_str_with_series_as_list_of_dicts

    def _write_series_dict_for_args_dict(
        self, args_dict: dict, class_str_with_series_as_list_of_dicts: classStrWithListOfEntriesAsListOfDicts
    ):
        existing_data = self._get_series_dict_with_data_class_for_args_dict(
            args_dict)
        if existing_data is missing_data:
            self._add_series_dict_for_args_dict(
                class_str_with_series_as_list_of_dicts
            )
        else:
            self._update_series_dict_for_args_dict(
                class_str_with_series_as_list_of_dicts
            )

    def _add_series_dict_for_args_dict(
        self, args_dict: dict, class_str_with_series_as_list_of_dicts: classStrWithListOfEntriesAsListOfDicts
    ):
        series_as_list_of_dicts = class_str_with_series_as_list_of_dicts.list_of_entries_as_list_of_dicts
        data_class = class_str_with_series_as_list_of_dicts

        object_to_insert = copy(args_dict)
        object_to_insert.update(
            dict(entry_series=series_as_list_of_dicts, data_class=data_class)
        )
        self._mongo.collection.insert_one(object_to_insert)

        return success

    def _update_series_dict_for_args_dict(
        self, args_dict: dict, class_str_with_series_as_list_of_dicts: classStrWithListOfEntriesAsListOfDicts
    ):

        series_as_list_of_dicts = class_str_with_series_as_list_of_dicts.list_of_entries_as_list_of_dicts
        data_class = class_str_with_series_as_list_of_dicts

        find_object_dict = args_dict
        find_object_dict["data_class"] = data_class
        new_values_dict = {"$set": {"entry_series": series_as_list_of_dicts}}
        self._mongo.collection.update_one(
            find_object_dict, new_values_dict, upsert=True
        )

        return success
