""""
FIXME

We only need this file until the old capital has been copied over

"""
from sysobjects.production.timed_storage import timedEntry, listOfEntries


class capitalEntry(timedEntry):
    @property
    def required_argument_names(self) -> list:
        return ["capital_value"]  # compulsory args

    @property
    def _name_(self):
        return "Capital"

    @property
    def containing_data_class_name(self):
        return "sysdata.production.capital.capitalForStrategy"


class capitalForStrategy(listOfEntries):
    """
    A list of capitalEntry
    """

    def _entry_class(self):
        return capitalEntry
