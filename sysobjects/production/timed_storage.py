from copy import copy
import datetime

import pandas as pd

from syscore.exceptions import missingData
from syscore.constants import arg_not_supplied, success

DATE_KEY_NAME = "date"


class timedEntry(object):
    """
    These four functions normally overriden by an inheriting class
    """

    @property
    def required_argument_names(self) -> list:
        ## We pass **kwargs and *args to these functions, but the args have to be given names
        return ["test1", "test2"]  # compulsory args

    @property
    def _name_(self) -> str:
        # name used for labelling so __repr__ can be generic
        return "timedEntry"

    @property
    def containing_data_class_name(self) -> str:
        ## this makes sure we don't mix and match different types of timed storage
        return "sysdata.production.generic_timed_storage.listOfEntries"

    def _argument_checks(self, kwargs: dict):
        ## used to check that certain kwargs meet certain filters
        ## inherited version should raise exception if problems
        pass

    def __init__(self, *args, date: datetime.datetime = arg_not_supplied):
        """
        Can pass either a single dict (which can include 'date') or the arguments in the order of required_arguments

        >>> timedEntry(1,2)._arg_dict_excluding_date
        {'test1': 1, 'test2': 2}
        >>> timedEntry(dict(test1=1, test2=2))._arg_dict_excluding_date
        {'test1': 1, 'test2': 2}
        >>> timedEntry(dict(test1=1, test2=2), date = datetime.datetime(2012,1,1))
        timedEntry 2012-01-01 00:00:00: {'test1': 1, 'test2': 2}
        >>> timedEntry(dict(test1=1, test2=2, date = datetime.datetime(2012,1,1)), date = datetime.datetime(2012,1,12))
        timedEntry 2012-01-01 00:00:00: {'test1': 1, 'test2': 2}
        """
        args_as_dict = self._resolve_args(args, date)

        self._argument_checks(args_as_dict)

        self._init_data_from_passed_args(args_as_dict)

    def _resolve_args(self, args: tuple, date: datetime.datetime) -> dict:
        ## We can either be passed a dict or a list of args
        ## If we're passed a dict, we put the date in if available
        ## Otherwise it's a list and
        if len(args) == 1:
            if isinstance(args[0], dict):
                args_as_dict = self._resolve_args_passed_as_dict(args, date)
                return args_as_dict

        args_as_dict = self._resolve_args_passed_as_star_args(args, date)

        return args_as_dict

    def _resolve_args_passed_as_dict(
        self, args: tuple, date: datetime.datetime
    ) -> dict:
        args_as_dict = args[0]
        if DATE_KEY_NAME not in args_as_dict:
            args_as_dict[DATE_KEY_NAME] = date

        return args_as_dict

    def _resolve_args_passed_as_star_args(
        self, args: tuple, date: datetime.datetime
    ) -> dict:

        required_args = self.required_argument_names
        try:
            assert len(required_args) == len(args)
        except BaseException:
            raise Exception(
                "Expecting to be passed arguments of length %d to match %s, instead got %d arguments"
                % (len(required_args), str(required_args), len(args))
            )

        args_as_dict = {}
        for arg_name, arg_value in zip(required_args, args):
            args_as_dict[arg_name] = arg_value

        args_as_dict[DATE_KEY_NAME] = date

        return args_as_dict

    def _init_data_from_passed_args(self, args_as_dict: dict):
        date = args_as_dict.pop(DATE_KEY_NAME)
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        assert type(date) is datetime.datetime

        self._date = date
        for arg_name in args_as_dict.keys():
            setattr(self, arg_name, args_as_dict[arg_name])

        self._arg_names = list(args_as_dict.keys())

    @property
    def date(self) -> datetime.datetime:
        return self._date

    @property
    def arg_names(self) -> list:
        return self._arg_names

    @property
    def _all_arg_names_including_date(self) -> list:
        return [DATE_KEY_NAME] + self.arg_names

    @property
    def _arg_dict_excluding_date(self) -> dict:
        result = dict([(key, getattr(self, key)) for key in self.arg_names])
        return result

    @property
    def _arg_dict_including_date(self) -> dict:
        result = dict(
            [(key, getattr(self, key)) for key in self._all_arg_names_including_date]
        )
        return result

    def __repr__(self):
        return "%s %s: %s" % (
            self._name_,
            self.date,
            str(self._arg_dict_excluding_date),
        )

    def as_dict(self):
        return self._arg_dict_including_date

    @classmethod
    def from_dict(timedEntry, entry_as_dict: dict):
        return timedEntry(entry_as_dict)

    def check_args_match(self, another_entry):
        my_args = self.arg_names
        another_args = another_entry.arg_names

        my_args.sort()
        another_args.sort()

        try:
            assert my_args == another_args
        except BaseException:
            raise Exception(
                "Parameters for %s (%s) don't match with %s"
                % (self._name_, my_args, another_args)
            )

        return success


class listOfEntriesAsListOfDicts(list):
    def as_list_of_entries(self, class_of_entry_list):
        class_of_each_individual_entry = class_of_entry_list.as_empty()._entry_class()
        list_of_class_entries = [
            class_of_each_individual_entry.from_dict(entry_as_dict)
            for entry_as_dict in self
        ]

        return class_of_entry_list(list_of_class_entries)

    def as_plain_list(self):
        return list(self)


class listOfEntries(list):
    """
    A list of timedEntry
    """

    def _entry_class(self):
        return timedEntry

    def __init__(self, list_of_entries: list):
        super().__init__([])
        self._arg_names = []
        for entry in list_of_entries:
            self.append(entry)

    @property
    def arg_names(self) -> list:
        return getattr(self, "_arg_names", [])

    def as_list_of_dict(self) -> list:
        list_of_dict = [entry.as_dict() for entry in self]

        return listOfEntriesAsListOfDicts(list_of_dict)

    @classmethod
    def from_list_of_dict(cls, list_of_dict: listOfEntriesAsListOfDicts):
        class_of_each_individual_entry = cls.as_empty()._entry_class()
        list_of_class_entries = [
            class_of_each_individual_entry.from_dict(entry_as_dict)
            for entry_as_dict in list_of_dict
        ]

        return cls(list_of_class_entries)

    @classmethod
    def as_empty(listOfEntries):
        return listOfEntries([])

    def sort(self):
        super().sort(key=lambda x: x.date)

    def final_entry(self):
        if len(self) == 0:
            raise missingData
        self.sort()
        return self[-1]

    def append(self, item):
        if len(self) > 0:
            previous_final_entry = self.final_entry()
            try:
                previous_final_entry.check_args_match(item)
            except Exception as e:
                raise Exception("%s ; can't add to list" % e)
        else:
            ## no entries yet, init argument names
            self._arg_names = item.arg_names

        super().append(item)

    def delete_last_entry(self):
        self.sort()
        self.pop()

    def _as_list_of_dates_and_dict_of_lists(self) -> (list, dict):
        """

        :return: list of lists; date
        """

        list_of_dates = [item.date for item in self]
        dict_of_lists = {}
        arg_names = self.arg_names

        for entry in self:
            for item_name in arg_names:
                existing_list = dict_of_lists.get(item_name, [])
                existing_list.append(getattr(entry, item_name, None))
                dict_of_lists[item_name] = existing_list

        return (list_of_dates, dict_of_lists)

    def as_pd_df(self):
        """

        :return: pd.DataFrame
        """
        if len(self) == 0:
            raise missingData
        (
            list_of_dates,
            dict_of_lists,
        ) = self._as_list_of_dates_and_dict_of_lists()

        self_as_df = pd.DataFrame(dict_of_lists, index=list_of_dates)
        self_as_df = self_as_df.sort_index()

        return self_as_df
