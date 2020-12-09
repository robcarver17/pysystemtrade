import time
from copy import  copy
import datetime
from sysdata.data_blob import dataBlob

from syscore.fileutils import get_filename_for_package
from syscontrol.data_interface import dataControlProcess
from syscontrol.data_interface import diagControlProcess
from syscontrol.data_objects import was_running_pid_notok_closed


def monitor():
    with dataBlob(log_name="system-monitor") as data:
        process_observatory = processObservatory(data)

        while 2==2:
            check_if_pid_running_and_if_not_finish(process_observatory)
            process_observatory.update_all_status_with_process_control()
            generate_html(process_observatory)
            time.sleep(300)

UNKNOWN_STATUS = "Unknown"

MAX_LOG_LENGTH = 20
class internal_logger(list):
    def append_msg(self, new_msg):
        if len(self)>MAX_LOG_LENGTH:
            del(self[0])
        self.append(new_msg)

    def html_repr(self):
        all_str = "<br/>".join(self)
        return all_str



class processObservatory(dict):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self._log_messages = internal_logger()

        ## get initial status
        self.update_all_status_with_process_control()


    def lol_repr(self):
        list_of_processes =get_list_of_process_names(self)
        list_of_str = [self.list_of_str_for_process(process_name)
                       for process_name in list_of_processes]

        return list_of_str

    def list_of_str_for_process(self, process_name):

        control_str = str(get_control_for_process(self, process_name))
        status_str = self.get_current_status(process_name)

        return [process_name, control_str, status_str]

    @property
    def data(self):
        return self._data

    @property
    def log_messages(self):
        return self._log_messages

    def update_all_status_with_process_control(self):
        list_of_process = get_list_of_process_names(self)
        for process_name in list_of_process:
            process_running_status = get_running_mode_str_for_process(self, process_name)
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


def get_running_mode_str_for_process(process_observatory: processObservatory, process_name: str):
    control = get_control_for_process(process_observatory, process_name)
    return control.running_mode_str()

def get_control_for_process(process_observatory: processObservatory, process_name: str):
    diag_control = diagControlProcess(process_observatory.data)
    control = diag_control.get_control_for_process_name(process_name)

    return control


def check_if_pid_running_and_if_not_finish(process_observatory: processObservatory):
    data_control = dataControlProcess(process_observatory.data)
    data_control.check_if_pid_running_and_if_not_finish_all_processes()

filename = "private.index.html"

def generate_html(process_observatory: processObservatory):
    resolved_filename = get_filename_for_package(filename)

    with open(resolved_filename, "w") as file:
        file.write("<br/> Last update %s" % str(datetime.datetime.now()))
        file.write("<br/><br/>")
        html_table(file, process_observatory.lol_repr())
        file.write("<br/><br/>")
        file.write(process_observatory.log_messages.html_repr())
        file.write("<br/><br/>")


def html_table(file, lol: list):
  file.write('<table>')
  for sublist in lol:
    file.write('  <tr><td>')
    file.write('    </td><td>'.join(sublist))
    file.write('  </td></tr>')
  file.write('</table>')

if __name__ == "__main__":
    monitor()