"""
Process control:

For a given process:
 - am I running?
 - when did I last finish running?
 - is my status NO-RUN, STOP or GO?
 - have I run today and finished running?
"""

from copy import copy
import datetime
import os
import pandas as pd

import psutil

from syscore.fileutils import html_table
from syscore.dateutils import SECONDS_PER_DAY, last_run_or_heartbeat_from_date_or_none

from syscore.objects import (
    success,
    failure,
    _named_object,
    missing_data,
)

process_stop = _named_object("process stop")
process_no_run = _named_object("process no run")
process_running = _named_object("process running")



go_status = "GO"
no_run_status = "NO-RUN"
stop_status = "STOP"
default_process_id = 0

possible_status = [go_status, no_run_status, stop_status]

start_run_idx = 0
end_run_idx = 1

missing_date_str=""

class dictOfRunningMethods(dict):
    def log_start_run_for_method(self, method_name: str):
        current_entry = self.get_current_entry(method_name)
        current_entry[start_run_idx] = datetime.datetime.now()
        self.set_entry(method_name, current_entry)

    def log_end_run_for_method(self, method_name: str):
        current_entry = self.get_current_entry(method_name)
        current_entry[end_run_idx] = datetime.datetime.now()
        self.set_entry(method_name, current_entry)

    def currently_running(self, method_name):
        last_start = self.when_last_start_run(method_name)
        last_end = self.when_last_end_run(method_name)
        if last_start is missing_data:
            return False
        if last_end is missing_data:
            return True

        if last_start>last_end:
            return True

        return False

    def when_last_start_run(self, method_name):
        current_entry = self.get_current_entry(method_name)
        start_run = current_entry[start_run_idx]
        if start_run == missing_date_str:
            return missing_data
        return start_run

    def when_last_end_run(self, method_name):
        current_entry = self.get_current_entry(method_name)
        end_run = current_entry[end_run_idx]
        if end_run == missing_date_str:
            return missing_data
        return end_run


    def as_dict(self):
        return dict(self)

    def get_current_entry(self, method_name) -> list:
        ans= copy(self.get(method_name, [missing_date_str, missing_date_str]))

        return ans

    def set_entry(self, method_name, new_entry):
        self[method_name] = new_entry

not_running = "not running"
still_running_and_pid_ok = "running"
was_running_pid_notok_closed = "crashed"



class controlProcess(object):
    def __init__(
        self,
        last_start_time: datetime.datetime=None,
        last_end_time: datetime.datetime=None,
        currently_running: bool=False,
        status: str=go_status,
        process_id: int=default_process_id,
        recently_crashed: bool = False,
        running_methods: dictOfRunningMethods = dictOfRunningMethods()
    ):
        assert status in possible_status
        self._last_start_time = last_start_time
        self._last_end_time = last_end_time
        self._currently_running = currently_running
        self._status = status
        self._process_id = process_id
        self._running_methods = running_methods
        self._recently_crashed = recently_crashed

    def __repr__(self):
        return " ".join(self.as_printable_list())


    @property
    def running_mode_str(self) -> str:
        if self.currently_running:
            run_string = still_running_and_pid_ok
        else:
            if self.recently_crashed:
                run_string = was_running_pid_notok_closed
            else:
                run_string = not_running

        return run_string

    @property
    def recently_crashed(self):
        return self._recently_crashed

    @property
    def running_methods(self) -> dictOfRunningMethods:
        return self._running_methods

    @property
    def process_id(self) -> int:
        return self._process_id

    @property
    def last_start_time(self) -> datetime.datetime:
        return self._last_start_time

    @property
    def last_end_time(self) -> datetime.datetime:
        return self._last_end_time

    @property
    def currently_running(self) -> bool:
        return self._currently_running

    @property
    def status(self) -> str:
        return self._status

    def as_dict(self):
        output = dict(
            last_start_time=self.last_start_time,
            last_end_time=self.last_end_time,
            status=self.status,
            currently_running=self.currently_running,
            process_id=self.process_id,
            running_methods = self.running_methods.as_dict(),
            recently_crashed = self.recently_crashed
        )

        return output

    @classmethod
    def from_dict(controlProcess, input_dict):
        input_dict['running_methods'] = dictOfRunningMethods(input_dict.get('running_methods', {}))
        control_process = controlProcess(**input_dict)

        return control_process

    def start_process(self) -> _named_object:
        result = self.check_if_okay_to_start_process()
        if result is not success:
            return result

        self._last_start_time = datetime.datetime.now()
        self._currently_running = True
        self._process_id = os.getpid()
        self._recently_crashed = False

        return success

    def check_if_pid_running_and_if_not_finish_return_status(self) -> str:
        if not self.currently_running:
            return not_running

        pid_running = self.check_if_pid_running()
        if pid_running:
            return still_running_and_pid_ok

        self.finish_process()
        self._recently_crashed = True

        return was_running_pid_notok_closed

    def finish_process(self) -> _named_object:
        """

        :return: success, or failure if no process running
        """

        if not self.currently_running:
            return failure

        self._last_end_time = datetime.datetime.now()
        self._currently_running = False
        self._process_id = default_process_id

        return success


    def check_if_okay_to_start_process(self) -> _named_object:
        """

        :return: success, or process_no_run, process_stop, process_running
        """
        if self.currently_running:
            return process_running

        if self.status == stop_status:
            return process_stop

        if self.status == no_run_status:
            return process_no_run

        return success


    def log_start_run_for_method(self, method_name: str):
        self.running_methods.log_start_run_for_method(method_name)

    def when_method_last_started(self, method_name: str):
        return self.running_methods.when_last_start_run(method_name)

    def log_end_run_for_method(self, method_name: str):
        self.running_methods.log_end_run_for_method(method_name)

    def when_method_last_ended(self, method_name: str):
        return self.running_methods.when_last_end_run(method_name)

    def method_currently_running(self, method_name: str):
        return self.running_methods.currently_running(method_name)


    def check_if_pid_running(self) -> bool:
        ## I don't normally make jokes in code, or use weird variable names, so allow me this one please
        flash_gordon_is_alive = is_pid_running(self.process_id)
        return flash_gordon_is_alive

    def check_if_process_status_stopped(self) -> bool:
        if self.status == stop_status:
            return True
        else:
            return False

    def has_process_finished_in_last_day(self) -> bool:
        if self.currently_running:
            return False

        end_time = self.last_end_time
        if not end_time:
            return False

        time_now = datetime.datetime.now()
        time_delta = time_now - end_time
        if time_delta.seconds <= SECONDS_PER_DAY:
            return True
        else:
            return False

    def change_status_to_stop(self):
        self._status = stop_status

    def change_status_to_go(self):
        self._status = go_status

    def change_status_to_no_run(self):
        self._status = no_run_status

    def as_printable_list(self):
        run_string = self.running_mode_str
        status_string = f"{''+self.status:<7}"
        process_id_string = f"{''+str(self.process_id):<8}"
        return ["Started %s" %
                last_run_or_heartbeat_from_date_or_none(self.last_start_time),
                "ended %s" %
                last_run_or_heartbeat_from_date_or_none(self.last_end_time),
                "Status %s" % status_string,
                "PID %s" % process_id_string,
                run_string
                ]

    def as_printable_dict(self) -> dict:
        run_string = self.running_mode_str
        return dict(start = last_run_or_heartbeat_from_date_or_none(self.last_start_time),
                    end = last_run_or_heartbeat_from_date_or_none(self.last_end_time),
                    status = self.status,
                    PID = self.process_id,
                    running = run_string
                    )


class dictOfControlProcesses(dict):
    def __repr__(self):
        return "\n".join(self.pretty_print_list())

    def pretty_print_list(self) -> list:
        ans = [self._pretty_print_element(key) for key in self.keys()]

        return ans

    def _pretty_print_element(self, key) -> str:
        name_string = f"{'' + key:<32}"
        all_string = name_string+str(self[key])

        return all_string

    def list_of_printable_lists(self) -> list:
        lol = [[key]+value.as_printable_list() for key, value in self.items()]
        return lol

    def to_html_table_in_file(self, file):
        html_table(file, self.list_of_printable_lists())

    def list_of_lists(self) -> list:
        lol = [value.as_printable_dict() for key, value in self.items()]

        return lol

    def as_pd_df(self) -> pd.DataFrame:
        pd_df = pd.DataFrame(self.list_of_lists())
        pd_df.index = list(self.keys())

        return pd_df


def list_of_all_running_pids():
    psid_list=[]
    for proc in psutil.process_iter():
        try:
            processID = proc.pid
            psid_list.append(processID)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return psid_list


def is_pid_running(pid):
    pid_list = list_of_all_running_pids()
    return pid in pid_list


