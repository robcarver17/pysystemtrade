from sysdata._DEPRECATED.mongo_log import mongoLogData
from sysdata.data_blob import dataBlob
from syslogdiag._DEPRECATED.database_log import logData
from sysproduction.data.generic_production_data import productionDataLayerGeneric

#### BASICALLY DEPRECATED KEEP ON TO CLEAN OLD LOGS OUT


class diagLogs(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_object(mongoLogData)
        return data

    @property
    def db_log_data(self) -> logData:
        return self.data.db_log

    def delete_log_items_from_before_n_days(self, days: int = 365):
        # need something to delete old log records, eg more than x months ago

        self.db_log_data.delete_log_items_from_before_n_days(lookback_days=days)
