import os
import shutil

from syscore.fileutils import get_resolved_pathname
from sysdata.private_config import (
    get_private_config_key_value,
    get_private_then_default_key_value,
)
from syscore.objects import missing_data
from sysdata.data_blob import dataBlob

from sysproduction.backup_arctic_to_csv import get_backup_dir as csv_backup_dir
from sysproduction.diagnostic.backtest_state import get_directory_store_backtests


def backup_files():
    data = dataBlob(log_name="backup_files")
    backup_object = backupFiles(data)
    backup_object.backup_files()

    return None


class backupFiles(object):
    def __init__(self, data):
        self.data = data

    def backup_files(self):
        data = self.data
        log = data.log
        log.msg("Exporting mongo data")
        dump_mongo_data(data)
        log.msg("Copying data to backup destination")
        backup_mongo_dump(data)
        backup_csv_dump(data)
        backup_state_files(data)


def dump_mongo_data(data):
    path = get_mongo_dump_directory()
    data.log.msg("Dumping mongo data to %s NOT TESTED IN WINDOWS" % path)
    os.system("mongodump -o=%s" % path)
    data.log.msg("Dumped")


def backup_mongo_dump(data):
    source_path = get_mongo_dump_directory()
    destination_path = get_mongo_backup_directory()
    shutil.rmtree(destination_path)
    data.log.msg("Copy from %s to %s" % (source_path, destination_path))
    shutil.copytree(source_path, destination_path)


def backup_csv_dump(data):
    source_path = get_csv_source_directory()
    destination_path = get_csv_backup_directory()
    data.log.msg("Copy from %s to %s" % (source_path, destination_path))
    os.system("rsync -av %s %s" % (source_path, destination_path))


def backup_state_files(data):
    source_path = get_statefile_directory()
    destination_path = get_statefile_backup_directory()
    data.log.msg("Copy from %s to %s" % (source_path, destination_path))
    os.system("rsync -av %s %s" % (source_path, destination_path))


# sources
def get_mongo_dump_directory():
    ans = get_private_then_default_key_value("mongo_dump_directory")
    return get_resolved_pathname(ans)


def get_csv_source_directory():
    ans = csv_backup_dir()
    return get_resolved_pathname(ans)


def get_statefile_directory():
    ans = get_directory_store_backtests()
    return get_resolved_pathname(ans)


# destintations
def get_csv_backup_directory():
    main_backup = get_main_backup_directory()
    ans = os.path.join(main_backup, "csv")

    return ans


def get_mongo_backup_directory():
    main_backup = get_main_backup_directory()
    ans = os.path.join(main_backup, "mongo")

    return ans


def get_statefile_backup_directory():
    main_backup = get_main_backup_directory()
    ans = os.path.join(main_backup, "statefile")

    return ans


def get_main_backup_directory():
    ans = get_private_config_key_value("offsystem_backup_directory")
    if ans is missing_data:
        raise Exception(
            "Can't backup without setting 'offsystem_backup_directory' in private_config.yaml"
        )
    return get_resolved_pathname(ans)
