import os
from sysdata.config.production_config import get_production_config

from sysproduction.data.directories import (
    get_mongo_dump_directory,
    get_mongo_backup_directory,
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


def dump_mongo_data(data: dataBlob):
    config = data.config
    host = config.get_element_or_arg_not_supplied("mongo_host")
    path = get_mongo_dump_directory()
    data.log.msg("Dumping mongo data to %s NOT TESTED IN WINDOWS" % path)
    if host.startswith("mongodb://"):
        os.system("mongodump --uri='%s' -o=%s" % (host, path))
    else:
        os.system("mongodump --host='%s' -o=%s" % (host, path))
    data.log.msg("Dumped")


def backup_mongo_dump(data):
    source_path = get_mongo_dump_directory()
    destination_path = get_mongo_backup_directory()
    data.log.msg("Copy from %s to %s" % (source_path, destination_path))
    os.system("rsync -av %s %s" % (source_path, destination_path))


if __name__ == "__main__":
    backup_mongo_data_as_dump()
