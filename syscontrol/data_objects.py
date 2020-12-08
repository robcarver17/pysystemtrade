"""
Process control:

For a given process:
 - am I running?
 - when did I last finish running?
 - is my status NO-RUN, STOP or GO?
 - have I run today and finished running?
"""
from dataclasses import dataclass
from copy import copy
import datetime
import os

import psutil
from sysdata.base_data import baseData
from syscore.objects import (
    success,
    failure,
    _named_object,
    missing_data,
)

from dataclasses import  dataclass

process_stop = _named_object("process stop")
process_no_run = _named_object("process no run")
process_running = _named_object("process running")


from syscore.dateutils import SECONDS_PER_DAY
from syslogdiag.log import logtoscreen

go_status = "GO"
no_run_status = "NO-RUN"
stop_status = "STOP"
default_id = 0
no_id = "None"

possible_status = [go_status, no_run_status, stop_status]

start_run_idx = 0
end_run_idx = 1

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
        return current_entry[start_run_idx]

    def when_last_end_run(self, method_name):
        current_entry = self.get_current_entry(method_name)
        return current_entry[end_run_idx]


    def as_dict(self):
        return dict(self)

    def get_current_entry(self, method_name):
        ans= copy(self.get(method_name, [missing_data, missing_data]))
        #FIXME
        if type(ans) is datetime.datetime:
            return [missing_data, missing_data]

    def set_entry(self, method_name, new_entry):
        self[method_name] = new_entry

class controlProcess(object):
    def __init__(
        self,
        last_start_time: datetime.datetime=None,
        last_end_time: datetime.datetime=None,
        currently_running: bool=False,
        status: str=go_status,
        process_id: int=default_id,
        running_methods: dictOfRunningMethods = dictOfRunningMethods()
    ):
        assert status in possible_status
        self._last_start_time = last_start_time
        self._last_end_time = last_end_time
        self._currently_running = currently_running
        self._status = status
        self._process_id = process_id
        self._running_methods = running_methods

    def __repr__(self):
        if self.currently_running:
            run_string = "running"
        else:
            run_string = "not running"
        status_string = f"{''+self.status:<7}"
        process_id_string = f"{''+str(self.process_id):<10}"
        return "Last started %s Last ended status %s %s PID %s is %s" % (
            self.last_start_time,
            self.last_end_time,
            status_string,
            process_id_string,
            run_string,
        )

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
            running_methods = self.running_methods.as_dict()
        )

        return output

    @classmethod
    def from_dict(controlProcess, input_dict):
        input_dict['running_methods'] = dictOfRunningMethods(input_dict.get('running_methods', {}))
        control_process = controlProcess(**input_dict)

        return control_process

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

    def start_process(self) -> _named_object:
        result = self.check_if_okay_to_start_process()
        if result is not success:
            return result

        self._last_start_time = datetime.datetime.now()
        self._currently_running = True
        self._process_id = os.getpid()

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

    def check_if_pid_running_and_if_not_finish(self):
        pid_running = self.check_if_pid_running()
        if not pid_running:
            self.finish_process()

    def check_if_pid_running(self) -> bool:
        ## I don't normally make jokes in code, or use weird variable names, so allow me this one please
        flash_gordon_is_alive = is_pid_running(self.process_id)
        return flash_gordon_is_alive

    def finish_process(self) -> _named_object:
        """

        :return: success, or failure if no process running
        """

        if not self.currently_running:
            return failure

        self._last_end_time = datetime.datetime.now()
        self._currently_running = False
        self._process_id = no_id

        return success

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


class controlProcessData(baseData):
    def __init__(self, log=logtoscreen("controlProcessData")):
        super().__init__(log=log)
        self._control_store = dict()

    def get_dict_of_control_processes(self) ->dict:
        list_of_names = self.get_list_of_process_names()
        output_dict = dict([(process_name, self._get_control_for_process_name(
            process_name)) for process_name in list_of_names])

        return output_dict

    def get_list_of_process_names(self) ->list:
        return list(self._control_store.keys())

    def _get_control_for_process_name(self, process_name) -> controlProcess:
        control = self._get_control_for_process_name_without_default(
            process_name)
        if control is missing_data:
            return controlProcess()
        else:
            return control

    def _get_control_for_process_name_without_default(self, process_name) -> controlProcess:
        control = self._control_store.get(process_name, missing_data)
        return control

    def _update_control_for_process_name(
            self, process_name, new_control_object):
        existing_control = self._get_control_for_process_name_without_default(
            process_name
        )
        if existing_control is missing_data:
            self._add_control_for_process_name(
                process_name, new_control_object)
        else:
            self._modify_existing_control_for_process_name(
                process_name, new_control_object
            )

    def _add_control_for_process_name(self, process_name, new_control_object):
        self._control_store[process_name] = new_control_object

    def _modify_existing_control_for_process_name(
        self, process_name, new_control_object
    ):
        self._control_store[process_name] = new_control_object

    def check_if_okay_to_start_process(self, process_name: str) -> _named_object:
        """

        :param process_name: str
        :return:  success, or if not okay: process_no_run, process_stop, process_running
        """
        original_process = self._get_control_for_process_name(process_name)
        result = original_process.check_if_okay_to_start_process()

        return result

    def start_process(self, process_name: str) -> _named_object:
        """

        :param process_name: str
        :return:  success, or if not okay: process_no_run, process_stop, process_running
        """
        original_process = self._get_control_for_process_name(process_name)
        result = original_process.start_process()
        if result is success:
            self._update_control_for_process_name(
                process_name, original_process)

        return result

    def finish_all_processes(self):

        list_of_names = self.get_list_of_process_names()
        _ = [self.finish_process(process_name) for process_name in list_of_names]

        return success

    def finish_process(self, process_name: str) -> _named_object:
        """

        :param process_name: str
        :return: sucess or failure if can't finish process (maybe already running?)
        """
        original_process = self._get_control_for_process_name(process_name)
        result = original_process.finish_process()
        if result is success:
            self._update_control_for_process_name(
                process_name, original_process)

        return result

    def check_if_process_status_stopped(self, process_name: str) -> bool:
        """

        :param process_name: str
        :return: bool
        """
        original_process = self._get_control_for_process_name(process_name)
        result = original_process.check_if_process_status_stopped()

        return result

    def has_process_finished_in_last_day(self, process_name:str) -> bool:
        """

        :param process_name: str
        :return: bool
        """
        original_process = self._get_control_for_process_name(process_name)
        result = original_process.has_process_finished_in_last_day()

        return result

    def change_status_to_stop(self, process_name: str):
        original_process = self._get_control_for_process_name(process_name)
        original_process.change_status_to_stop()
        self._update_control_for_process_name(process_name, original_process)

    def change_status_to_go(self, process_name: str):
        original_process = self._get_control_for_process_name(process_name)
        original_process.change_status_to_go()
        self._update_control_for_process_name(process_name, original_process)

    def change_status_to_no_run(self, process_name: str):
        original_process = self._get_control_for_process_name(process_name)
        original_process.change_status_to_no_run()
        self._update_control_for_process_name(process_name, original_process)

    def log_start_run_for_method(self, process_name: str, method_name: str):
        original_process = self._get_control_for_process_name(process_name)
        original_process.log_start_run_for_method(method_name)
        self._update_control_for_process_name(process_name, original_process)

    def log_end_run_for_method(self, process_name: str, method_name: str):
        original_process = self._get_control_for_process_name(process_name)
        original_process.log_end_run_for_method(method_name)
        self._update_control_for_process_name(process_name, original_process)

    def when_method_last_started(self, process_name: str, method_name: str) -> datetime.datetime:
        original_process = self._get_control_for_process_name(process_name)
        return original_process.when_method_last_started(method_name)

    def when_method_last_ended(self, process_name: str, method_name: str) -> datetime.datetime:
        original_process = self._get_control_for_process_name(process_name)
        return original_process.when_method_last_ended(method_name)

    def method_currently_running(self, process_name: str, method_name: str) -> bool:
        original_process = self._get_control_for_process_name(process_name)
        return original_process.method_currently_running()


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