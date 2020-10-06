"""
Generic timed storage; more bullet proof than a data frame
"""

import datetime
import pandas as pd

from syscore.objects import (
    arg_not_supplied,
    missing_data,
    success,
    failure,
    resolve_function,
)
from sysdata.data import baseData
from syslogdiag.log import logtoscreen


class timedEntry(object):
    """
    These three functions normally overriden
    """

    def _setup_args_data(self):
        self._star_args = ["test1", "test2"]  # compulsory args

    def _name_(self):
        return "timedEntry"

    def _containing_data_class_name(self):
        return "sysdata.production.generic_timed_storage.listOfEntries"

    def _kwargs_checks(self, kwargs):
        return success

    def __init__(self, *args, date=arg_not_supplied):
        self._setup_args_data()

        kwargs = self._resolve_args(args, date)

        self._kwargs_checks(kwargs)

        date = kwargs.pop("date")
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        self.date = date

        for arg_name in kwargs.keys():
            setattr(self, arg_name, kwargs[arg_name])

        self._arg_names = list(kwargs.keys())
        self._dict_args = kwargs

        self._full_dict = dict(date=date)
        self._full_dict.update(kwargs)

    def _resolve_args(self, args, date):

        if len(args) == 1:
            if isinstance(args[0], dict):
                entry_as_dict = args[0]
                if "date" not in entry_as_dict:
                    entry_as_dict["date"] = arg_not_supplied

                return entry_as_dict

        return self._resolve_args_normally(args, date)

    def _resolve_args_normally(self, args, date):

        star_args = self._star_args
        try:
            assert len(star_args) == len(args)
        except BaseException:
            raise Exception(
                "Expecting to be passed arguments of length %d to match %s, instead got %d arguments" %
                (len(star_args), str(star_args), len(args)))

        new_kwargs = {}
        for arg_name, arg_value in zip(star_args, args):
            new_kwargs[arg_name] = arg_value
        new_kwargs["date"] = date

        return new_kwargs

    def __repr__(self):
        return "%s %s: %s" % (self._name_(), self.date, self._dict_args)

    def as_dict(self):
        return self._full_dict

    @classmethod
    def from_dict(timedEntry, entry_as_dict):
        return timedEntry(entry_as_dict)

    def check_match(self, another_entry):
        my_args = self._arg_names
        another_args = another_entry._arg_names

        my_args.sort()
        another_args.sort()

        try:
            assert my_args == another_args
        except BaseException:
            raise Exception(
                "Parameters for %s (%s) don't match with %s" % self._name_(),
                my_args,
                another_args,
            )

        return success


class listOfEntries(list):
    """
    A list of timedEntry
    """

    def _entry_class(self):
        return timedEntry

    def __init__(self, list_of_entries):
        super().__init__([])
        self._arg_names = []
        for entry in list_of_entries:
            self.append(entry)

    def as_list_of_dict(self):
        list_of_dict = [entry.as_dict() for entry in self]

        return list_of_dict

    @classmethod
    def from_list_of_dict(cls, list_of_dict):
        entry_class = cls.as_empty()._entry_class()
        list_of_class_entries = [entry_class.from_dict(
            entry_as_dict) for entry_as_dict in list_of_dict]

        return cls(list_of_class_entries)

    @classmethod
    def as_empty(listOfEntries):
        return listOfEntries([])

    def sort(self):
        super().sort(key=lambda x: x.date)

    def final_entry(self):
        if len(self) == 0:
            return missing_data

        self.sort()
        return self[-1]

    def append(self, item):
        self.sort()
        previous_final = self.final_entry()
        if len(self) > 0:
            try:
                previous_final.check_match(item)
            except Exception as e:
                raise Exception("%s ; can't add to list" % e)

        super().append(item)
        item_arg_names = item._arg_names
        self._arg_names = list(set(self._arg_names + item_arg_names))

    def delete_last_entry(self):
        self.sort()
        self.pop()

    def _as_list_of_lists(self):
        """

        :return: list of lists; date
        """

        list_of_dates = [item.date for item in self]
        dict_of_lists = {}
        arg_names = self._arg_names

        for entry in self:
            for item_name in arg_names:
                existing_list = dict_of_lists.get(item_name, [])
                existing_list.append(getattr(entry, item_name, None))
                dict_of_lists[item_name] = existing_list

        return [list_of_dates, dict_of_lists]

    def as_pd_df(self):
        """

        :return: pd.DataFrame
        """
        if len(self) == 0:
            return missing_data
        (
            list_of_dates,
            dict_of_lists,
        ) = self._as_list_of_lists()

        self_as_df = pd.DataFrame(dict_of_lists, index=list_of_dates)
        self_as_df = self_as_df.sort_index()

        return self_as_df


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
