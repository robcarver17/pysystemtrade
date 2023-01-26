from syscore.constants import arg_not_supplied
from syscore.exceptions import existingData
from sysdata.mongodb.mongo_connection import mongoDb
from sysdata.mongodb.mongo_generic import mongoDataWithSingleKey, MONGO_ID_KEY
from syscore.dateutils import long_to_datetime, datetime_to_long

from syslogdiag.log_to_screen import logtoscreen
from syslogdiag.log_entry import (
    LEVEL_ID,
    TIMESTAMP_ID,
    TEXT_ID,
    LOG_RECORD_ID,
    logEntry,
)
from syslogdiag.database_log import logToDb, logData

from copy import copy
import datetime

LOG_COLLECTION_NAME = "Logs"


class logToMongod(logToDb):
    """
    Logs to a mongodb

    """

    def __init__(
        self,
        type: str,
        data=None,
        log_level: str = "Off",
        mongo_db: mongoDb = arg_not_supplied,
        **kwargs,
    ):
        super().__init__(type=type, data=data, log_level=log_level, **kwargs)
        self._mongo_data = mongoDataWithSingleKey(
            LOG_COLLECTION_NAME, LOG_RECORD_ID, mongo_db=mongo_db
        )

    @property
    def mongo_data(self):
        return self._mongo_data

    def get_next_log_id(self) -> int:
        # slightly complicated to deal with race conditions
        invalid_id = True
        counter = 0
        while invalid_id:
            last_id = self._get_last_used_log_id()
            next_id = last_id + 1
            reserved_okay = self._reserve_log_id(next_id)
            if reserved_okay:
                break
            counter = counter + 1
            if counter > 100:
                raise Exception("Couldn't reserve log ID")

        return next_id

    def _get_last_used_log_id(self) -> int:
        """
        Get last used log id. Returns None if not present

        :return: int or None
        """
        current_max = self.mongo_data.get_max_of_keys()
        if current_max == None:
            return 0

        return current_max

    def _reserve_log_id(self, next_id: int) -> bool:
        try:
            self.mongo_data.add_data(next_id, {})
        except existingData:
            return False
        else:
            return True

    def add_log_record(self, log_entry: logEntry):
        record_as_dict = log_entry.log_as_dict()
        key = record_as_dict[LOG_RECORD_ID]

        self.mongo_data.add_data(key, record_as_dict, allow_overwrite=True)


class mongoLogData(logData):
    def __init__(
        self, mongo_db: mongoDb = arg_not_supplied, log=logtoscreen("mongoLogData")
    ):
        self._mongo_data = mongoDataWithSingleKey(
            collection_name=LOG_COLLECTION_NAME,
            key_name=LOG_RECORD_ID,
            mongo_db=mongo_db,
        )
        super().__init__(log=log)

    @property
    def mongo_data(self):
        return self._mongo_data

    def get_log_items_as_entries(
        self, attribute_dict: dict = arg_not_supplied, lookback_days: int = 1
    ):
        """
        Return log items not as text, good for diagnostics

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of 4-typles: timestamp, level, text, attributes
        """
        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        attribute_dict = add_after_n_days_to_attribute_dict(
            attribute_dict, lookback_days=lookback_days
        )

        results_list = self.mongo_data.get_list_of_result_dict_for_custom_dict(
            attribute_dict
        )

        # ... to list of log entries
        list_of_log_items = [
            mongoLogEntry.log_entry_from_dict(single_log_dict)
            for single_log_dict in results_list
        ]

        # sort by log ID
        list_of_log_items.sort(key=lambda x: x._log_id)

        return list_of_log_items

    def delete_log_items_from_before_n_days(self, lookback_days=365):
        # need something to delete old log records, eg more than x months ago

        attribute_dict = add_before_n_days_to_attribute_dict(
            {}, lookback_days=lookback_days
        )
        self.mongo_data.delete_data_with_any_warning_for_custom_dict(attribute_dict)


def add_before_n_days_to_attribute_dict(
    attribute_dict: dict, lookback_days: int
) -> dict:
    attribute_dict = add_timestamp_cutoff_to_attribute_dict(
        attribute_dict=attribute_dict,
        lookback_days=lookback_days,
        greater_or_less_than="$lt",
    )

    return attribute_dict


def add_after_n_days_to_attribute_dict(
    attribute_dict: dict, lookback_days: int
) -> dict:

    attribute_dict = add_timestamp_cutoff_to_attribute_dict(
        attribute_dict=attribute_dict,
        lookback_days=lookback_days,
        greater_or_less_than="$gt",
    )

    return attribute_dict


def add_timestamp_cutoff_to_attribute_dict(
    attribute_dict: dict, lookback_days: int, greater_or_less_than: str = "$gt"
) -> dict:
    assert greater_or_less_than in ["$gt", "$lt"]
    timestamp_dict = {}
    timestamp_dict[greater_or_less_than] = cutoff_date_as_long_n_days_before(
        lookback_days
    )
    attribute_dict[TIMESTAMP_ID] = timestamp_dict

    return attribute_dict


def cutoff_date_as_long_n_days_before(lookback_days: int) -> int:
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=lookback_days)

    return datetime_to_long(cutoff_date)


class mongoLogEntry(logEntry):
    @classmethod
    def log_entry_from_dict(mongoLogEntry, log_dict_input: dict):
        """
        Starting with the dictionary representation, recover the original logEntry

        :param log_dict: dict, as per logEntry.log_dict()
        :return: logEntry object
        """
        log_dict = copy(log_dict_input)
        log_timestamp_aslong = log_dict.pop(TIMESTAMP_ID)
        msg_level = log_dict.pop(LEVEL_ID)
        text = log_dict.pop(TEXT_ID)
        log_id = log_dict.pop(LOG_RECORD_ID)
        attributes = log_dict

        log_timestamp = long_to_datetime(log_timestamp_aslong)

        log_entry = mongoLogEntry(
            text,
            log_timestamp=log_timestamp,
            msglevel=msg_level,
            attributes=attributes,
            log_id=log_id,
        )

        return log_entry
