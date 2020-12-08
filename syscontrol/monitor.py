from copy import  copy
import datetime
from sysdata.data_blob import dataBlob

from syscore.fileutils import get_filename_for_package
from syscontrol.data_interface import dataControlProcess
from syscontrol.data_interface import diagControlProcess
from syscontrol.data_objects import was_running_pid_notok_closed


def monitor():
    with dataBlob(log_name="system-monitor") as data:
        while 2==2:
            process_observatory = processObservatory(data)
            check_if_pid_running_return_status_msgs(process_observatory)
            process_observatory.update_all_status_with_process_control()
            generate_html(process_observatory)

UNKNOWN_STATUS = "Unknown"
RUNNING_STATUS = "Running"
NOT_RUNNING_STATUS = "Not running"
PID_CRASHED_STATUS = "Not running: Crashed"

MAX_LOG_LENGTH = 15
class internal_logger(list):
    def append_msg(self, new_msg):
        if len(self)>MAX_LOG_LENGTH:
            del(self[0])
        self.append(new_msg)



class processObservatory(dict):
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

    def mark_as_pid_crash_detected(self, process_name):
        self.update_status(process_name, PID_CRASHED_STATUS)

    def update_all_status_with_process_control(self):
        list_of_process = get_list_of_process_names(self)
        for process_name in list_of_process:
            currently_running = is_process_currently_running(self, process_name)
            if currently_running:
                self.update_status(process_name, RUNNING_STATUS)
            else:
                self.update_status(process_name, NOT_RUNNING_STATUS)

    def update_status(self, process_name, new_status):
        current_status = self.get_current_status(process_name)
        if current_status == new_status:
            pass
        elif current_status == PID_CRASHED_STATUS and new_status == NOT_RUNNING_STATUS:
            pass
        else:
            self.change_status(process_name, new_status)
            self.send_update_message(process_name, current_status, new_status)

    def send_update_message(self, process_name, current_status, new_status):
        ## Called when anything changes status
        msg = "Status of %s changed from %s to %s at %s" % (process_name, current_status, new_status,
                                                            str(datetime.datetime.now()))
        self.log_messages.append_msg(msg)

    def change_status(self, process_name, new_status):
        self[process_name] = new_status

    def get_current_status(self, process_name):
        status = copy(self.get(process_name, UNKNOWN_STATUS))
        return status

def get_list_of_process_names(process_observatory: processObservatory):
    diag_control = diagControlProcess(process_observatory.data)
    return diag_control.get_list_of_process_names()


def is_process_currently_running(process_observatory: processObservatory, process_name: str):
    control = get_control_for_process(process_observatory, process_name)
    if control.currently_running ==0:
        return False
    else:
        return True

def get_control_for_process(process_observatory: processObservatory, process_name: str):
    diag_control = diagControlProcess(process_observatory.data)
    control = diag_control.get_control_for_process_name(process_name)

    return control


def check_if_pid_running_return_status_msgs(process_observatory: processObservatory):
    data_control = dataControlProcess(process_observatory.data)

    results = data_control.check_if_pid_running_and_if_not_finish_all_processes()
    for process_result in results:
        process_name, pid_status = process_result
        if pid_status is was_running_pid_notok_closed:
            process_observatory.mark_as_pid_crash_detected(process_name)

    return results

filename = "private.index.html"

def generate_html(process_observatory: processObservatory):
    resolved_filename = get_filename_for_package(filename)

    with open(resolved_filename, "w") as file:
        file.write(str(process_observatory))
        file.write(str(process_observatory.log_messages))



if __name__ == "__main__":
    monitor()