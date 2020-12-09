import os

from syscore.fileutils import get_resolved_pathname
from sysdata.private_config import get_main_backup_directory
from sysdata.data_blob import dataBlob

from sysproduction.diagnostic.backtest_state import get_directory_store_backtests


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


def get_statefile_directory():
    ans = get_directory_store_backtests()
    return get_resolved_pathname(ans)


# destintations

def get_statefile_backup_directory():
    main_backup = get_main_backup_directory()
    ans = os.path.join(main_backup, "statefile")

    return ans


