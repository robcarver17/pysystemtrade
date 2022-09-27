"""
Generic timed storage; more bullet proof than a data frame
"""

from syscore.objects import (
    success,
    failure,
    resolve_function,
    arg_not_supplied,
    missing_data,
)
from sysdata.base_data import baseData
from syslogdiag.log_to_screen import logtoscreen
from sysobjects.production.timed_storage import (
    listOfEntriesAsListOfDicts,
    listOfEntries,
    timedEntry,
)


class classWithListOfEntriesAsListOfDicts(object):
    def __init__(
        self,
        class_of_entry_list,
        list_of_entries_as_list_of_dicts: listOfEntriesAsListOfDicts,
    ):
        self.class_of_entry_list = class_of_entry_list
        self.list_of_entries_as_list_of_dicts = list_of_entries_as_list_of_dicts

    def as_list_of_entries(self):
        return self.list_of_entries_as_list_of_dicts.as_list_of_entries(
            self.class_of_entry_list
        )


class classStrWithListOfEntriesAsListOfDicts(object):
    def __init__(
        self,
        class_of_entry_list_as_str: str,
        list_of_entries_as_list_of_dicts: listOfEntriesAsListOfDicts,
    ):
        self.class_of_entry_list_as_str = class_of_entry_list_as_str
        self.list_of_entries_as_list_of_dicts = list_of_entries_as_list_of_dicts

    def with_class_object(self):

        class_of_entry_list = resolve_function(self.class_of_entry_list_as_str)

        return classWithListOfEntriesAsListOfDicts(
            class_of_entry_list, self.list_of_entries_as_list_of_dicts
        )

    def as_list_of_entries(self):
        with_class_object = self.with_class_object()
        return with_class_object.as_list_of_entries()

    def entry_list_as_plain_list(self):
        return self.list_of_entries_as_list_of_dicts.as_plain_list()


class listOfEntriesData(baseData):
    """
    base data class for list of entries

    Highly generic, an args dict is any set of labels eg strategy & instrument for positions

    Most of the methods are private because when we inherit we don't want to see them
    """

    def _data_class_name(self) -> str:
        ## The type of storage we are putting in here
        return "sysdata.production.generic_timed_storage.listOfEntries"

    @property
    def _data_class(self):
        class_name = self._data_class_name()
        return resolve_function(class_name)

    @property
    def _empty_data_series(self):
        data_class = self._data_class
        data_class_instance = data_class([])
        empty_entry_series = data_class_instance.as_empty()

        return empty_entry_series

    def __init__(self, log=logtoscreen("listOfEntriesData")):

        super().__init__(log=log)

    def _delete_all_data_for_args_dict(
        self, args_dict: dict, are_you_really_sure: bool = False
    ):

        if not are_you_really_sure:
            self.log.warn("To delete all data, need to set are_you_really_sure=True")
            return failure

        empty_entry_series = self._empty_data_series
        self._write_series_for_args_dict(args_dict, empty_entry_series)

    def _update_entry_for_args_dict(self, new_entry: timedEntry, args_dict: dict):

        existing_series = self._get_series_for_args_dict(args_dict)
        if len(existing_series) > 0:
            # Check types match
            self._check_class_name_matches_for_new_entry(args_dict, new_entry)
        else:
            # empty this ensures we use the correct type for a new set of data
            existing_series = get_empty_series_for_timed_entry(new_entry)

        try:
            existing_series.append(new_entry)
        except Exception as e:
            error_msg = "Error %s when updating for %s with %s" % (
                str(e),
                str(args_dict),
                str(new_entry),
            )

            self.log.critical(error_msg)
            raise Exception(error_msg)

        class_of_entry_list_as_str = new_entry.containing_data_class_name

        self._write_series_for_args_dict(
            args_dict,
            existing_series,
            class_of_entry_list_as_str=class_of_entry_list_as_str,
        )

        return success

    def _check_class_name_matches_for_new_entry(
        self, args_dict: dict, new_entry: timedEntry
    ):

        entry_class_name_new_entry = new_entry.containing_data_class_name
        entry_class_name_existing = self._get_class_of_entry_list_as_str(args_dict)

        split_new_name = entry_class_name_new_entry.split(".")[-1]
        split_existing_name = entry_class_name_existing.split(".")[-1]
        try:
            assert split_new_name == split_existing_name
        except BaseException:
            error_msg = (
                "You tried to add an entry of type %s to existing data type %s"
                % (entry_class_name_new_entry, entry_class_name_existing)
            )
            self.log.critical(error_msg)
            raise Exception(error_msg)

    def _delete_last_entry_for_args_dict(self, args_dict, are_you_sure=False):
        if not are_you_sure:
            self.log.warn("Have to set are_you_sure to True when deleting")
            return failure
        entry_series = self._get_series_for_args_dict(args_dict)
        try:
            entry_series.delete_last_entry()
        except IndexError:
            self.log.warn(
                "Can't delete last entry for %s, as none present" % str(args_dict)
            )
            return failure

        self._write_series_for_args_dict(args_dict, entry_series)
        return success

    def _get_current_entry_for_args_dict(self, args_dict):
        entry_series = self._get_series_for_args_dict(args_dict)
        current_entry = entry_series.final_entry()

        return current_entry

    def _get_series_for_args_dict(self, args_dict) -> listOfEntries:
        class_with_series_as_list_of_dicts = (
            self._get_series_dict_and_class_for_args_dict(args_dict)
        )
        if class_with_series_as_list_of_dicts is missing_data:
            return self._empty_data_series

        entry_series = class_with_series_as_list_of_dicts.as_list_of_entries()

        return entry_series

    def _get_series_dict_and_class_for_args_dict(
        self, args_dict: dict
    ) -> classWithListOfEntriesAsListOfDicts:

        class_str_with_series_as_list_of_dicts = (
            self._get_series_dict_with_data_class_for_args_dict(args_dict)
        )

        if class_str_with_series_as_list_of_dicts is missing_data:
            return missing_data

        class_with_series_as_list_of_dicts = (
            class_str_with_series_as_list_of_dicts.with_class_object()
        )

        return class_with_series_as_list_of_dicts

    def _write_series_for_args_dict(
        self,
        args_dict: dict,
        entry_series: listOfEntries,
        class_of_entry_list_as_str: str = arg_not_supplied,
    ):
        entry_series_as_list_of_dicts = entry_series.as_list_of_dict()

        if class_of_entry_list_as_str is arg_not_supplied:
            class_of_entry_list_as_str = self._get_class_of_entry_list_as_str(args_dict)

        class_str_with_series_as_list_of_dicts = classStrWithListOfEntriesAsListOfDicts(
            class_of_entry_list_as_str, entry_series_as_list_of_dicts
        )

        self._write_series_dict_for_args_dict(
            args_dict, class_str_with_series_as_list_of_dicts
        )

        return success

    def _get_class_of_entry_list_as_str(
        self,
        args_dict: dict,
    ) -> str:

        ## Use existing data, or if not available use the default for this object
        class_str_with_series_as_list_of_dicts = (
            self._get_series_dict_with_data_class_for_args_dict(args_dict)
        )

        if class_str_with_series_as_list_of_dicts is missing_data:
            return self._data_class_name()
        else:
            return class_str_with_series_as_list_of_dicts.class_of_entry_list_as_str

    def _get_series_dict_with_data_class_for_args_dict(
        self, args_dict: dict
    ) -> classStrWithListOfEntriesAsListOfDicts:

        # return data_class, series_as_list_of_dicts
        ## return missing_data if unvailable
        raise NotImplementedError("Need to use child class")

    def _write_series_dict_for_args_dict(
        self,
        args_dict: dict,
        class_str_with_series_as_list_of_dicts: classStrWithListOfEntriesAsListOfDicts,
    ):
        raise NotImplementedError("Need to use child class")

    def _get_list_of_args_dict(self) -> list:
        raise NotImplementedError("Need to use child class")


def get_empty_series_for_timed_entry(new_entry: timedEntry) -> listOfEntries:
    containing_data_class_name = new_entry.containing_data_class_name
    containing_data_class = resolve_function(containing_data_class_name)

    return containing_data_class.as_empty()
