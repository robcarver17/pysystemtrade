from syscore.constants import arg_not_supplied

from sysdata.mongodb.mongo_generic import mongoDataWithMultipleKeys
from syslogdiag.log_to_screen import logtoscreen

DATA_CLASS_KEY = "data_class"
ENTRY_SERIES_KEY = "entry_series"


class mongoListOfEntriesData(object):
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
