import datetime
from syscore.constants import arg_not_supplied
from sysdata.mongodb.mongo_log import mongoLogData
from sysdata.data_blob import dataBlob
from syslogdiag.database_log import logToDb, logData
from sysproduction.data.generic_production_data import productionDataLayerGeneric


class diagLogs(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_object(mongoLogData)
        return data

    @property
    def db_log_data(self) -> logData:
        return self.data.db_log

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
        results = self.db_log_data.get_log_items(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        return results

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

        self.db_log_data.print_log_items(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )

    def find_last_entry_date(
        self, attribute_dict=arg_not_supplied, lookback_days=30
    ) -> datetime.datetime:
        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        last_entry_date = self.db_log_data.find_last_entry_date(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        return last_entry_date

    def delete_log_items_from_before_n_days(self, days: int = 365):
        # need something to delete old log records, eg more than x months ago

        self.db_log_data.delete_log_items_from_before_n_days(lookback_days=days)

    def get_possible_log_level_mapping(self) -> dict:
        return self.db_log_data.get_possible_log_level_mapping()

    def get_unique_list_of_values_for_log_attribute(
        self,
        attribute_name: str,
        attribute_dict: str = arg_not_supplied,
        lookback_days: int = 1,
    ) -> list:
        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        unique_list_of_values = (
            self.db_log_data.get_unique_list_of_values_for_log_attribute(
                attribute_name,
                attribute_dict=attribute_dict,
                lookback_days=lookback_days,
            )
        )

        return unique_list_of_values

    def get_list_of_unique_log_attribute_keys(
        self, attribute_dict: dict = arg_not_supplied, lookback_days: int = 1
    ) -> list:

        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        unique_list_of_log_attribute_keys = (
            self.db_log_data.get_list_of_unique_log_attribute_keys(
                attribute_dict=attribute_dict, lookback_days=lookback_days
            )
        )

        return unique_list_of_log_attribute_keys

    def get_log_items_with_level(
        self,
        log_level: str,
        attribute_dict: dict = arg_not_supplied,
        lookback_days: int = 1,
    ) -> list:
        if attribute_dict is arg_not_supplied:
            attribute_dict = {}

        list_of_log_items = self.db_log_data.get_log_items_with_level(
            log_level, attribute_dict=attribute_dict, lookback_days=lookback_days
        )

        return list_of_log_items
