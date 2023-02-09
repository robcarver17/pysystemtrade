from sysdata.production.timed_storage import (
    listOfEntriesData,
    classStrWithListOfEntriesAsListOfDicts,
    listOfEntriesAsListOfDicts,
)
from syscore.constants import arg_not_supplied

from sysdata.mongodb.mongo_generic import mongoDataWithMultipleKeys
from syslogdiag.log_to_screen import logtoscreen

DATA_CLASS_KEY = "data_class"
ENTRY_SERIES_KEY = "entry_series"


class mongoListOfEntriesData(listOfEntriesData):
    """
    Read and write data class to get capital for each strategy


    """

    @property
    def _collection_name(self) -> str:
        raise NotImplementedError("Need to inherit for a specific data type")

    @property
    def _data_name(self) -> str:
        raise NotImplementedError("Need to inherit for a specific data type")

    def __init__(
        self, mongo_db=arg_not_supplied, log=logtoscreen("mongoStrategyCapitalData")
    ):

        super().__init__(log=log)
        self._mongo_data = mongoDataWithMultipleKeys(
            self._collection_name, mongo_db=mongo_db
        )

    @property
    def mongo_data(self):
        return self._mongo_data

    def __repr__(self):
        return "Data connection for %s, mongodb %s" % (
            self._data_name,
            str(self.mongo_data),
        )

    def _get_list_of_args_dict(self) -> list:
        dict_list = self.mongo_data.get_list_of_all_dicts()
        _ = [dict_entry.pop(DATA_CLASS_KEY) for dict_entry in dict_list]
        _ = [dict_entry.pop(ENTRY_SERIES_KEY) for dict_entry in dict_list]

        return dict_list

    def _get_series_dict_with_data_class_for_args_dict(
        self, args_dict: dict
    ) -> classStrWithListOfEntriesAsListOfDicts:

        result_dict = self.mongo_data.get_result_dict_for_dict_keys(args_dict)

        data_class = result_dict[DATA_CLASS_KEY]
        series_as_list_of_dicts = result_dict[ENTRY_SERIES_KEY]
        series_as_list_of_dicts = listOfEntriesAsListOfDicts(series_as_list_of_dicts)

        class_str_with_series_as_list_of_dicts = classStrWithListOfEntriesAsListOfDicts(
            data_class, series_as_list_of_dicts
        )

        return class_str_with_series_as_list_of_dicts

    def _write_series_dict_for_args_dict(
        self,
        args_dict: dict,
        class_str_with_series_as_list_of_dicts: classStrWithListOfEntriesAsListOfDicts,
    ):

        series_as_plain_list = (
            class_str_with_series_as_list_of_dicts.entry_list_as_plain_list()
        )
        data_class = class_str_with_series_as_list_of_dicts.class_of_entry_list_as_str

        data_dict = {ENTRY_SERIES_KEY: series_as_plain_list, DATA_CLASS_KEY: data_class}

        self.mongo_data.add_data(args_dict, data_dict, allow_overwrite=True)
