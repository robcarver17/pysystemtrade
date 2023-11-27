import os
from sysdata.config.production_config import get_production_config

from sysproduction.data.directories import get_parquet_backup_directory

from sysdata.data_blob import dataBlob


def backup_parquet_data_to_remote():
    data = dataBlob(log_name="backup_mongo_data_as_dump")
    backup_object = backupParquet(data)
    backup_object.backup_parquet()

    return None


def get_parquet_directory(data):
    return data.parquet_root_directory


class backupParquet(object):
    def __init__(self, data):
        self.data = data

    def backup_parquet(self):
        data = self.data
        log = data.log
        log.debug("Copying data to backup destination")
        backup_parquet_data_to_remote_with_data(data)


def backup_parquet_data_to_remote_with_data(data):
    source_path = get_parquet_directory(data)
    destination_path = get_parquet_backup_directory()
    data.log.debug("Copy from %s to %s" % (source_path, destination_path))
    os.system("rsync -av %s %s" % (source_path, destination_path))


if __name__ == "__main__":
    backup_parquet_data_to_remote()
