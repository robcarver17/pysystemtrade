import os
from os.path import join as join_file_and_path

from syscore.constants import missing_data, missing_file
from syscore.fileutils import get_resolved_pathname, does_resolved_filename_exist

from sysdata.config.production_config import get_production_config

from syslogdiag.pst_logger import pst_logger, DEFAULT_LOG_LEVEL
from syslogdiag.log_entry import logEntry
from syslogdiag.email_via_db_interface import send_production_mail_msg

EMAIL_ON_LOG_LEVEL = [4]
LINES_TO_FLUSH_AFTER = 5


class logToFile(pst_logger):
    """
    Logs to a file, named after type

    """

    def __init__(
        self,
        type,
        data: "dataBlob" = None,
        log_level: str = DEFAULT_LOG_LEVEL,
        **kwargs,
    ):
        self.data = data
        self._log_directory = get_logging_directory(data)
        super().__init__(type=type, log_level=log_level, **kwargs)

    def log_handle_caller(
        self, msglevel: int, text: str, attributes: dict, log_id: int
    ):
        """
        Ignores log_level - logs everything, just in case

        Doesn't raise exceptions

        """
        log_entry = logEntry(
            text, msglevel=msglevel, attributes=attributes, log_id=log_id
        )
        print(log_entry)
        self.log_to_file(log_entry)

        if msglevel in EMAIL_ON_LOG_LEVEL:
            # Critical, send an email
            self.email_user(log_entry)

        return log_entry

    def log_to_file(self, log_entry: logEntry):
        self.log_file_handle.write("%s\n" % str(log_entry))
        self.check_if_ready_and_if_so_flush()

    def check_if_ready_and_if_so_flush(self):
        log_id = self.log_id
        if (log_id % LINES_TO_FLUSH_AFTER) == 0:
            self.log_file_handle.flush()

    def get_next_log_id(self) -> int:
        current_log_id = self.log_id
        incremented_log_id = current_log_id + 1
        self._logid = incremented_log_id

        return incremented_log_id

    @property
    def log_id(self) -> int:
        current_log_id = getattr(self, "_logid", None)
        if current_log_id is None:
            current_log_id = 0
            self.log_id = current_log_id

        return current_log_id

    @log_id.setter
    def log_id(self, log_id: int):
        self._logid = log_id

    def email_user(self, log_entry: logEntry):
        data = self.data
        subject_line = str(log_entry.attributes) + ": " + str(log_entry.text)

        log_entry_text = str(log_entry)
        send_production_mail_msg(
            data, log_entry_text, "*CRITICAL* ERROR: %s" % subject_line
        )

    def close_log_file(self):
        file_handle = getattr(self, "_file_handle", None)
        if file_handle is None:
            ## no file, logging won't work
            print("No log file open to close")
        else:
            file_handle.close()

            ## force reopen on new log
            self._file_handle = missing_file

    @property
    def log_file_handle(self):
        file_handle = getattr(self, "_file_handle", missing_file)
        if file_handle is missing_file:
            filename = self.log_filename_with_path
            file_handle = open(filename, "a", 5)

            self._file_handle = file_handle

        return file_handle

    @property
    def log_filename_with_path(self) -> str:
        log_directory = self.log_directory
        log_type = self.type
        log_filename = "log_%s.txt" % log_type
        log_filename_and_path = join_file_and_path(log_directory, log_filename)

        return log_filename_and_path

    @property
    def log_directory(self) -> str:
        return self._log_directory

    @property
    def type(self) -> str:
        return self.attributes["type"]


def get_logging_directory(data: "dataBlob"):
    config = get_production_config()
    log_dir = config.get_element_or_default("log_directory", None)
    if log_dir is None:
        ## Can't log this but print anyway
        print(
            "*** log_directory undefined in private_config.yaml, will log to arbitrary directory"
        )
        return missing_data

    log_dir = get_resolved_pathname(log_dir)
    try:
        os.mkdir(log_dir)
    except:
        pass

    return log_dir
