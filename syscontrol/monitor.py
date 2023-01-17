import time
from copy import copy
import datetime
from sysdata.data_blob import dataBlob

from syscore.fileutils import resolve_path_and_filename_for_package
from sysproduction.data.control_process import dataControlProcess
from sysproduction.data.control_process import diagControlProcess
from syscore.dateutils import date_as_short_pattern_or_question_if_missing
from syscontrol.list_running_pids import describe_trading_server_login_data


def monitor():
    with dataBlob(log_name="system-monitor") as data:
        process_observatory = processMonitor(data)
        while 2 == 2:
            check_if_pid_running_and_if_not_finish(process_observatory)
            process_observatory.update_all_status_with_process_control()
            generate_html(process_observatory)
            time.sleep(300)


UNKNOWN_STATUS = "Unknown"

MAX_LOG_LENGTH = 17


class internal_logger(list):
    def append_msg(self, new_msg):
        if len(self) > MAX_LOG_LENGTH:
            del self[0]
        self.append(new_msg)

    def html_repr(self, file):
        all_str = "<br/>".join(self)
        file.write(all_str)


class processMonitor(dict):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self._log_messages = internal_logger()

        ## get initial status
        self.update_all_status_with_process_control()

    @property
    def data(self):
        return self._data

    @property
    def log_messages(self):
        return self._log_messages

    def process_dict_to_html_table(self, file):
        data_control = dataControlProcess(self.data)
        dict_of_process = data_control.get_dict_of_control_processes()
        dict_of_process.to_html_table_in_file(file)

    def log_messages_to_html(self, file):
        self.log_messages.html_repr(file)

    def update_all_status_with_process_control(self):
        list_of_process = get_list_of_process_names(self)
        for process_name in list_of_process:
            process_running_status = get_running_mode_str_for_process(
                self, process_name
            )
            self.update_status(process_name, process_running_status)

    def update_status(self, process_name, new_status):
        current_status = self.get_current_status(process_name)
        if current_status == new_status:
            pass
        else:
            self.change_status(process_name, new_status)
            self.send_update_message(process_name, current_status, new_status)

    def send_update_message(self, process_name, current_status, new_status):
        ## Called when anything changes status
        msg = "Status of %s changed from %s to %s at %s" % (
            process_name,
            current_status,
            new_status,
            date_as_short_pattern_or_question_if_missing(datetime.datetime.now()),
        )
        self.log_messages.append_msg(msg)

    def change_status(self, process_name, new_status):
        self[process_name] = new_status

    def get_current_status(self, process_name):
        status = copy(self.get(process_name, UNKNOWN_STATUS))
        return status


def get_list_of_process_names(process_observatory: processMonitor):
    diag_control = diagControlProcess(process_observatory.data)
    return diag_control.get_list_of_process_names()


def get_running_mode_str_for_process(
    process_observatory: processMonitor, process_name: str
):
    control = get_control_for_process(process_observatory, process_name)
    return control.running_mode_str


def get_control_for_process(process_observatory: processMonitor, process_name: str):
    diag_control = diagControlProcess(process_observatory.data)
    control = diag_control.get_control_for_process_name(process_name)

    return control


def check_if_pid_running_and_if_not_finish(process_observatory: processMonitor):
    data_control = dataControlProcess(process_observatory.data)
    data_control.check_if_pid_running_and_if_not_finish_all_processes()


filename = "private.index.html"


def generate_html(process_observatory: processMonitor):
    resolved_filename = resolve_path_and_filename_for_package(filename)
    trading_server_description = describe_trading_server_login_data()
    dbase_description = str(process_observatory.data.mongo_db)
    with open(resolved_filename, "w") as file:
        file.write("<br/> Last update %s" % str(datetime.datetime.now()))
        file.write("<br/><br/>")
        file.write(
            "Monitoring machine %s with database %s"
            % (trading_server_description, dbase_description)
        )
        file.write("<br/><br/>")
        process_observatory.process_dict_to_html_table(file)
        file.write("<br/><br/>")
        process_observatory.log_messages_to_html(file)
        file.write("<br/><br/>")


if __name__ == "__main__":
    monitor()
