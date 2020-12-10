"""
Generic timed storage; more bullet proof than a data frame
"""

from syscore.objects import (
    arg_not_supplied,
    missing_data,
    success,
    failure,
    resolve_function,
)
from sysdata.base_data import baseData
from syslogdiag.log import logtoscreen


class listOfEntriesData(baseData):
    """
    base data class
    """

    def _name(self):
        return "listOfEntries"

    def _data_class_name(self):
        return "sysdata.production.generic_timed_storage.listOfEntries"

    def __init__(self, log=logtoscreen("listOfEntriesData")):

        super().__init__(log=log)
        self.name = self._name()

    def _delete_all_data_for_args_dict(
            self, args_dict, are_you_really_sure=False):
        if not are_you_really_sure:
            self.log.warn(
                "To delete all data, need to set are_you_really_sure=True")
            return failure

        data_class_name = self._data_class_name()
        data_class = resolve_function(data_class_name)
        entry_series = data_class.as_empty()

        self._write_series_for_args_dict(args_dict, entry_series)

    def _update_entry_for_args_dict(self, new_entry, args_dict):

        data_class_new_entry = new_entry._containing_data_class_name()
        entry_series = self._get_series_for_args_dict(args_dict)

        if len(entry_series) > 0:
            # Check types match
            existing_data_class_name = self._get_data_class_name_for_args_dict(
                args_dict
            )
            new_data_class = data_class_new_entry.split(".")[-1]
            existing_data_class = existing_data_class_name.split(".")[-1]
            try:
                assert new_data_class == existing_data_class
            except BaseException:
                self.log.warn(
                    "You tried to add an entry of type %s to existing data type %s" %
                    (data_class_new_entry, existing_data_class_name))
                return failure

        try:
            entry_series.append(new_entry)
        except Exception as e:
            self.log.warn(
                "Error %s when updating for %s with %s"
                % (str(e), str(args_dict), str(new_entry))
            )
            return failure

        self._write_series_for_args_dict(
            args_dict, entry_series, data_class_name=data_class_new_entry
        )

        return success

    def _delete_last_entry_for_args_dict(self, args_dict, are_you_sure=False):
        if not are_you_sure:
            self.log.warn("Have to set are_you_sure to True when deleting")
            return failure
        entry_series = self._get_series_for_args_dict(args_dict)
        try:
            entry_series.delete_last_entry()
        except IndexError:
            self.log.warn(
                "Can't delete last entry for %s, as none present" %
                str(args_dict))
            return failure

        self._write_series_for_args_dict(args_dict, entry_series)
        return success

    def _get_current_entry_for_args_dict(self, args_dict):
        entry_series = self._get_series_for_args_dict(args_dict)
        current_entry = entry_series.final_entry()

        return current_entry

    def _get_series_for_args_dict(self, args_dict):
        data_class, series_as_dict = self._get_series_dict_and_class_for_args_dict(
            args_dict)
        if series_as_dict is missing_data:
            return data_class.as_empty()

        entry_series = data_class.from_list_of_dict(series_as_dict)

        return entry_series

    def _get_series_dict_and_class_for_args_dict(self, args_dict):

        series_as_dict_with_data_class = (
            self._get_series_dict_with_data_class_for_args_dict(args_dict)
        )
        data_class_name = self._get_data_class_name_for_args_dict(
            args_dict, series_as_dict_with_data_class=series_as_dict_with_data_class)
        __, series_as_dict = series_as_dict_with_data_class
        data_class = resolve_function(data_class_name)

        return data_class, series_as_dict

    def _get_data_class_name_for_args_dict(
        self, args_dict, series_as_dict_with_data_class=arg_not_supplied
    ):
        if series_as_dict_with_data_class is arg_not_supplied:
            series_as_dict_with_data_class = (
                self._get_series_dict_with_data_class_for_args_dict(args_dict)
            )
        data_class_name, __ = series_as_dict_with_data_class

        if data_class_name is missing_data:
            # Return defaults
            data_class_name = self._data_class_name()

        return data_class_name

    def _write_series_for_args_dict(
        self, args_dict, entry_series, data_class_name=arg_not_supplied
    ):
        entry_series_as_list_of_dicts = entry_series.as_list_of_dict()
        if data_class_name is arg_not_supplied:
            data_class_name = self._get_data_class_name_for_args_dict(
                args_dict)

        self._write_series_dict_for_args_dict(
            args_dict, entry_series_as_list_of_dicts, data_class_name
        )

        return success

    def _get_series_dict_with_data_class_for_args_dict(self, args_dict):
        # return data_class, series_as_list_of_dicts
        raise NotImplementedError("Need to use child class")

    def _write_series_dict_for_args_dict(
        self, args_dict, series_as_list_of_dicts, data_class
    ):
        raise NotImplementedError("Need to use child class")

    def _get_list_of_args_dict(self):
        raise NotImplementedError("Need to use child class")
