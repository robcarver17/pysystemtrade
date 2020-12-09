import os
import shutil

from syscore.fileutils import get_resolved_pathname
from sysdata.private_config import get_main_backup_directory

from sysdata.private_config import (
    get_private_then_default_key_value,
)
from sysdata.data_blob import dataBlob


def backup_mongo_data_as_dump():
    data = dataBlob(log_name="backup_mongo_data_as_dump")
    backup_object = backupMongo(data)
    backup_object.backup_mongo_data_as_dump()

    return None


class backupMongo(object):
    def __init__(self, data):
        self.data = data

    def backup_mongo_data_as_dump(self):
        data = self.data
        log = data.log
        log.msg("Exporting mongo data")
        dump_mongo_data(data)
        log.msg("Copying data to backup destination")
        backup_mongo_dump(data)


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





# sources
def get_mongo_dump_directory():
    ans = get_private_then_default_key_value("mongo_dump_directory")
    return get_resolved_pathname(ans)


# destintations
def get_mongo_backup_directory():
    main_backup = get_main_backup_directory()
    ans = os.path.join(main_backup, "mongo")

    return ans



