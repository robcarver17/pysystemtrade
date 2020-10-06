import itertools

from syscore.objects import missing_data
from syslogdiag.log import logger, logEntry, LEVEL_ID, INVERSE_MAP

from sysproduction.diagnostic.emailing import send_production_mail_msg

LOG_COLLECTION_NAME = "Logs"
EMAIL_ON_LOG_LEVEL = [4]


class logToDb(logger):
    """
    Logs to a database

    """

    def __init__(self, type, data=None, log_level="Off", **kwargs):
        self.data = data
        super().__init__(type=type, log_level=log_level, **kwargs)

    def log_handle_caller(self, msglevel, text, input_attributes, log_id):
        """
        Ignores log_level - logs everything, just in case

        Doesn't raise exceptions

        """
        log_entry = logEntry(
            text,
            msglevel=msglevel,
            input_attributes=input_attributes,
            log_id=log_id)
        print(log_entry)

        self.add_log_record(log_entry)

        if msglevel in EMAIL_ON_LOG_LEVEL:
            # Critical, send an email
            self.email_user(log_entry)

        return log_entry

    def add_log_record(self, log_entry):
        raise NotImplementedError

    def email_user(self, log_entry):
        data = self.data
        try:
            send_production_mail_msg(data, str(log_entry), "*CRITICAL ERROR*")
        except BaseException:
            self.error("Couldn't email user")


class logData(object):
    def __init__(self):
        pass

    def get_log_items_with_level(
        self, log_level, attribute_dict=dict(), lookback_days=1
    ):
        attribute_dict[LEVEL_ID] = log_level

        ans = self.get_log_items(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )

        return ans

    def get_possible_log_level_mapping(self):
        return INVERSE_MAP

    def get_list_of_values_for_log_attribute(
        self, attribute_name, attribute_dict={}, lookback_days=7
    ):
        list_of_log_attributes = self.get_list_of_log_attributes(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        list_of_values = [
            log_attr.get(
                attribute_name,
                None) for log_attr in list_of_log_attributes]
        list_of_values = [
            value for value in list_of_values if value is not None]
        unique_list_of_values = list(set(list_of_values))

        return unique_list_of_values

    def get_list_of_unique_log_attribute_keys(
            self, attribute_dict={}, lookback_days=1):
        list_of_log_attributes = self.get_list_of_log_attributes(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        list_of_list_of_log_attribute_keys = [
            list(log_attr.keys()) for log_attr in list_of_log_attributes
        ]
        list_of_log_attribute_keys = itertools.chain.from_iterable(
            list_of_list_of_log_attribute_keys
        )
        unique_list_of_log_attribute_keys = list(
            set(list_of_log_attribute_keys))

        return unique_list_of_log_attribute_keys

    def get_list_of_log_attributes(self, attribute_dict={}, lookback_days=1):
        list_of_log_items = self.get_log_items(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        list_of_log_attributes = [
            log_item.attributes for log_item in list_of_log_items]

        return list_of_log_attributes

    def get_log_items(self, attribute_dict=dict(), lookback_days=1):
        """
        Return log items as list of text

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of str
        """

        results = self.get_log_items_as_entries(
            attribute_dict, lookback_days=lookback_days
        )

        return results

    def print_log_items(self, attribute_dict=dict(), lookback_days=1):
        """
        Print log items as list of text

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of str
        """

        results = self.get_log_items(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        # jam together as text
        results_as_text = [str(log_entry) for log_entry in results]

        print("\n".join(results_as_text))

    def find_last_entry_date(self, attribute_dict=dict(), lookback_days=30):
        results = self.get_log_items_as_entries(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        time_stamps = [entry.timestamp for entry in results]
        if len(time_stamps) == 0:
            return missing_data
        return max(time_stamps)

    def get_log_items_as_entries(self, attribute_dict=dict(), lookback_days=1):
        """
        Return log items not as text, good for diagnostics

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of 4-typles: timestamp, level, text, attributes
        """

        raise NotImplementedError

    def delete_log_items_from_before_n_days(self, days=365):
        # need something to delete old log records, eg more than x months ago

        raise NotImplementedError
