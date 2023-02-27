import datetime
import itertools

from syscore.constants import arg_not_supplied
from syscore.exceptions import missingData
from sysdata.base_data import baseData
from syslogdiag.logger import logger, DEFAULT_LOG_LEVEL
from syslogdiag.log_entry import INVERSE_MAP, LEVEL_ID, logEntry
from syslogdiag.log_to_screen import logtoscreen

from syslogdiag.email_via_db_interface import send_production_mail_msg

LOG_COLLECTION_NAME = "Logs"
EMAIL_ON_LOG_LEVEL = [4]


class logToDb(logger):
    """
    Logs to a database

    """

    def __init__(
        self,
        type,
        data: "dataBlob" = None,
        log_level: str = DEFAULT_LOG_LEVEL,
        **kwargs,
    ):
        self.data = data
        super().__init__(type=type, log_level=log_level, **kwargs)

    def log_handle_caller(
        self, msglevel: int, text: str, attributes: dict, log_id: int
    ):
        """
        Ignores log_level - logs everything, just in case

        Doesn't raise exceptions

        """
        log_entry = logEntry(
            text, msglevel=msglevel, attributes=attributes, log_id=log_id
        )
        print(log_entry)

        self.add_log_record(log_entry)

        if msglevel in EMAIL_ON_LOG_LEVEL:
            # Critical, send an email
            self.email_user(log_entry)

        return log_entry

    def add_log_record(self, log_entry):
        raise NotImplementedError

    def email_user(self, log_entry: logEntry):
        data = self.data
        subject_line = str(log_entry.attributes) + ": " + str(log_entry.text)

        log_entry_text = str(log_entry)
        send_production_mail_msg(
            data, log_entry_text, "*CRITICAL* ERROR: %s" % subject_line
        )


class logData(baseData):
    def __init__(self, log: logger = logtoscreen("logData")):
        super().__init__(log=log)

    def get_log_items_with_level(
        self,
        msg_level: int,
        attribute_dict: dict = arg_not_supplied,
        lookback_days: int = 1,
    ) -> list:

        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        attribute_dict[LEVEL_ID] = msg_level

        list_of_log_items = self.get_log_items(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )

        return list_of_log_items

    def get_possible_log_level_mapping(self) -> dict:
        return INVERSE_MAP

    def get_unique_list_of_values_for_log_attribute(
        self,
        attribute_name: str,
        attribute_dict: dict = arg_not_supplied,
        lookback_days: int = 7,
    ) -> list:

        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        list_of_log_attributes = self.get_list_of_log_attributes(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )

        list_of_values = [
            log_attr.get(attribute_name, None) for log_attr in list_of_log_attributes
        ]

        list_of_values = [value for value in list_of_values if value is not None]
        unique_list_of_values = list(set(list_of_values))

        return unique_list_of_values

    def get_list_of_unique_log_attribute_keys(
        self, attribute_dict: dict = arg_not_supplied, lookback_days: int = 1
    ) -> list:

        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        list_of_log_attributes = self.get_list_of_log_attributes(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        list_of_list_of_log_attribute_keys = [
            list(log_attr.keys()) for log_attr in list_of_log_attributes
        ]
        list_of_log_attribute_keys = itertools.chain.from_iterable(
            list_of_list_of_log_attribute_keys
        )
        unique_list_of_log_attribute_keys = list(set(list_of_log_attribute_keys))

        return unique_list_of_log_attribute_keys

    def get_list_of_log_attributes(
        self, attribute_dict: dict = arg_not_supplied, lookback_days: int = 1
    ) -> list:

        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        list_of_log_items = self.get_log_items(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        list_of_log_attributes = [log_item.attributes for log_item in list_of_log_items]

        return list_of_log_attributes

    def get_log_items(
        self, attribute_dict: dict = arg_not_supplied, lookback_days: int = 1
    ) -> list:
        """
        Return log items as list of text

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of str
        """
        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        list_of_log_items = self.get_log_items_as_entries(
            attribute_dict, lookback_days=lookback_days
        )

        return list_of_log_items

    def print_log_items(
        self, attribute_dict: dict = arg_not_supplied, lookback_days: int = 1
    ):
        """
        Print log items as list of text

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of str
        """
        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        results = self.get_log_items(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        # jam together as text
        results_as_text = [str(log_entry) for log_entry in results]

        print("\n".join(results_as_text))

    def find_last_entry_date(
        self, attribute_dict: dict = arg_not_supplied, lookback_days: int = 7
    ) -> datetime.datetime:

        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        results = self.get_log_items_as_entries(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        time_stamps = [entry.timestamp for entry in results]
        if len(time_stamps) == 0:
            raise missingData

        last_entry_date = max(time_stamps)
        return last_entry_date

    def get_log_items_as_entries(
        self, attribute_dict: dict = arg_not_supplied, lookback_days: int = 1
    ) -> list:

        """
        Return log items not as text, good for diagnostics

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of 4-typles: timestamp, level, text, attributes
        """

        raise NotImplementedError

    def delete_log_items_from_before_n_days(self, lookback_days: int = 365):
        # need something to delete old log records, eg more than x months ago

        raise NotImplementedError
