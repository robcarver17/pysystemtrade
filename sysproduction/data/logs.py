from syscore.objects import arg_not_supplied
from sysdata.mongodb.mongo_log import mongoLogData
from sysdata.data_blob import dataBlob


class diagLogs(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoLogData)
        self.data = data

    def get_log_items(self, attribute_dict=dict(), lookback_days=1):
        """
        Return log items as list of text

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of str
        """
        results = self.data.db_log.get_log_items(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        return results

    def print_log_items(self, attribute_dict=dict(), lookback_days=1):
        """
        Print log items as list of text

        :param attribute_dict: dictionary of attributes to return logs for
        :return: list of str
        """

        self.data.db_log.print_log_items(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )

    def find_last_entry_date(self, attribute_dict=dict(), lookback_days=30):
        results = self.data.db_log.find_last_entry_date(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        return results

    def delete_log_items_from_before_n_days(self, days=365):
        # need something to delete old log records, eg more than x months ago

        self.data.db_log.delete_log_items_from_before_n_days(days=days)

    def get_possible_log_level_mapping(self):
        return self.data.db_log.get_possible_log_level_mapping()

    def get_list_of_values_for_log_attribute(
        self, attribute_name, attribute_dict={}, lookback_days=1
    ):

        return self.data.db_log.get_list_of_values_for_log_attribute(
            attribute_name, attribute_dict=attribute_dict, lookback_days=lookback_days)

    def get_list_of_unique_log_attribute_keys(
            self, attribute_dict={}, lookback_days=1):
        return self.data.db_log.get_list_of_unique_log_attribute_keys(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )

    def get_log_items_with_level(
        self, log_level, attribute_dict=dict(), lookback_days=1
    ):
        return self.data.db_log.get_log_items_with_level(
            log_level, attribute_dict=attribute_dict, lookback_days=lookback_days)
