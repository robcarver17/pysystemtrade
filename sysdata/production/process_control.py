"""
Process control:

For a given process:
 - am I running?
 - when did I last finish running?
 - is my status NO-RUN, STOP or GO?
 - have I run today and finished running?
"""
import datetime
import os

from sysdata.data import baseData
from syscore.objects import (
    success,
    failure,
    process_no_run,
    process_stop,
    process_running,
    missing_data,
)
from syscore.dateutils import SECONDS_PER_DAY
from syslogdiag.log import logtoscreen

go_status = "GO"
no_run_status = "NO-RUN"
stop_status = "STOP"
default_id = "?"
no_id = "None"

possible_status = [go_status, no_run_status, stop_status]


class controlProcess(object):
    def __init__(
        self,
        last_start_time=None,
        last_end_time=None,
        currently_running=False,
        status="GO",
        process_id=default_id,
    ):
        assert status in possible_status
        self._last_start_time = last_start_time
        self._last_end_time = last_end_time
        self._currently_running = currently_running
        self._status = status
        self._process_id = process_id

    def __repr__(self):
        if self.currently_running:
            run_string = "running"
        else:
            run_string = "not running"
        return "Last started %s Last ended %s is %s, status %s, PID %s" % (
            self.last_start_time,
            self.last_end_time,
            run_string,
            self.status,
            str(self.process_id),
        )

    @property
    def process_id(self):
        return self._process_id

    @property
    def last_start_time(self):
        return self._last_start_time

    @property
    def last_end_time(self):
        return self._last_end_time

    @property
    def currently_running(self):
        return self._currently_running

    @property
    def status(self):
        return self._status

    def as_dict(self):
        output = dict(
            last_start_time=self.last_start_time,
            last_end_time=self.last_end_time,
            status=self.status,
            currently_running=self.currently_running,
            process_id=self.process_id,
        )

        return output

    @classmethod
    def from_dict(controlProcess, input_dict):
        control_process = controlProcess(**input_dict)

        return control_process

    def check_if_okay_to_start_process(self):
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

    def start_process(self):
        result = self.check_if_okay_to_start_process()
        if result is not success:
            return result

        self._last_start_time = datetime.datetime.now()
        self._currently_running = True
        self._process_id = os.getpid()

        return success

    def finish_process(self):
        """

        :return: success, or failure if no process running
        """

        if not self.currently_running:
            return failure

        self._last_end_time = datetime.datetime.now()
        self._currently_running = False
        self._process_id = no_id

        return success

    def check_if_process_status_stopped(self):
        if self.status == stop_status:
            return True
        else:
            return False

    def has_process_finished_in_last_day(self):
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
        self.log = log
        self._control_store = dict()

    def get_dict_of_control_processes(self):
        list_of_names = self.get_list_of_process_names()
        output_dict = dict([(process_name, self._get_control_for_process_name(
            process_name)) for process_name in list_of_names])

        return output_dict

    def get_list_of_process_names(self):
        return self._control_store.keys()

    def _get_control_for_process_name(self, process_name):
        control = self._get_control_for_process_name_without_default(
            process_name)
        if control is missing_data:
            return controlProcess()
        else:
            return control

    def _get_control_for_process_name_without_default(self, process_name):
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

    def check_if_okay_to_start_process(self, process_name):
        """

        :param process_name: str
        :return:  success, or if not okay: process_no_run, process_stop, process_running
        """
        original_process = self._get_control_for_process_name(process_name)
        result = original_process.check_if_okay_to_start_process()

        return result

    def start_process(self, process_name):
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

    def finish_process(self, process_name):
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

    def check_if_process_status_stopped(self, process_name):
        """

        :param process_name: str
        :return: bool
        """
        original_process = self._get_control_for_process_name(process_name)
        result = original_process.check_if_process_status_stopped()

        return result

    def has_process_finished_in_last_day(self, process_name):
        """

        :param process_name: str
        :return: bool
        """
        original_process = self._get_control_for_process_name(process_name)
        result = original_process.has_process_finished_in_last_day()

        return result

    def change_status_to_stop(self, process_name):
        original_process = self._get_control_for_process_name(process_name)
        original_process.change_status_to_stop()
        self._update_control_for_process_name(process_name, original_process)

    def change_status_to_go(self, process_name):
        original_process = self._get_control_for_process_name(process_name)
        original_process.change_status_to_go()
        self._update_control_for_process_name(process_name, original_process)

    def change_status_to_no_run(self, process_name):
        original_process = self._get_control_for_process_name(process_name)
        original_process.change_status_to_no_run()
        self._update_control_for_process_name(process_name, original_process)
