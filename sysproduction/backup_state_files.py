import os

from sysproduction.data.directories import (
    get_statefile_directory,
    get_statefile_backup_directory,
)
from sysdata.data_blob import dataBlob


def backup_state_files():
    data = dataBlob(log_name="backup_state_files")
    backup_object = backupStateFiles(data)
    backup_object.backup_files()

    return None


class backupStateFiles(object):
    def __init__(self, data):
        self.data = data

    def backup_files(self):
        data = self.data
        self.data.log.msg("Backing up state files")
        backup_state_files_with_data_object(data)


def backup_state_files_with_data_object(data):
    source_path = get_statefile_directory()
    destination_path = get_statefile_backup_directory()
    data.log.msg("Copy from %s to %s" % (source_path, destination_path))
    os.system("rsync -av %s %s" % (source_path, destination_path))


if __name__ == "__main__":
    backup_state_files()
