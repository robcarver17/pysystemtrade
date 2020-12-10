import datetime
import socket

from syscore.dateutils import SECONDS_PER_HOUR
from syscore.genutils import str2Bool
from sysdata.data_blob import dataBlob
from sysdata.mongodb.mongo_process_control import mongoControlProcessData

import yaml
from syscore.fileutils import get_filename_for_package
from syscore.objects import missing_data, arg_not_supplied

PRIVATE_CONTROL_CONFIG_FILE = get_filename_for_package("private.private_control_config.yaml")
PUBLIC_CONTROL_CONFIG_FILE = get_filename_for_package("syscontrol.control_config.yaml")




class dataControlProcess(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoControlProcessData)
        self.data = data

    def get_dict_of_control_processes(self):
        return self.data.db_control_process.get_dict_of_control_processes()


    def check_if_okay_to_start_process(self, process_name):
        """

        :param process_name: str
        :return:  success, or if not okay: process_no_run, process_stop, process_running
        """
        return self.data.db_control_process.check_if_okay_to_start_process(
            process_name)

    def start_process(self, process_name):
        """

        :param process_name: str
        :return:  success, or if not okay: process_no_run, process_stop, process_running
        """
        return self.data.db_control_process.start_process(process_name)

    def finish_process(self, process_name):
        """

        :param process_name: str
        :return: sucess or failure if can't finish process (maybe already running?)
        """

        return self.data.db_control_process.finish_process(process_name)

    def finish_all_processes(self):

        return self.data.db_control_process.finish_all_processes()

    def check_if_pid_running_and_if_not_finish_all_processes(self) -> list:
        return self.data.db_control_process.check_if_pid_running_and_if_not_finish_all_processes()

    def check_if_process_status_stopped(self, process_name):
        """

        :param process_name: str
        :return: bool
        """
        return self.data.db_control_process.check_if_process_status_stopped(
            process_name
        )

    def change_status_to_stop(self, process_name):
        self.data.db_control_process.change_status_to_stop(process_name)

    def change_status_to_go(self, process_name):
        self.data.db_control_process.change_status_to_go(process_name)

    def change_status_to_no_run(self, process_name):
        self.data.db_control_process.change_status_to_no_run(process_name)

    def has_process_finished_in_last_day(self, process_name):
        result = self.data.db_control_process.has_process_finished_in_last_day(
            process_name
        )
        return result

    def log_start_run_for_method(self, process_name: str, method_name: str):
       self.data.db_control_process.log_start_run_for_method(process_name, method_name)

    def log_end_run_for_method(self, process_name: str, method_name: str):
       self.data.db_control_process.log_end_run_for_method(process_name, method_name)


class diagControlProcess:
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()
        data.add_class_object(mongoControlProcessData)

        self.data = data

    def get_config_dict(self, process_name: str) -> dict:
        previous_process = self.previous_process_name(process_name)
        start_time = self.get_start_time(process_name)
        end_time = self.get_stop_time(process_name)
        machine_name = self.required_machine_name(process_name)

        result_dict = dict(
            previous_process=previous_process,
            start_time=start_time,
            end_time=end_time,
            machine_name=machine_name
        )

        return result_dict

    def get_process_status_dict(self, process_name: str) -> dict:
        time_to_stop = self.is_it_time_to_stop(process_name)
        time_to_start = self.is_it_time_to_run(process_name)
        prev_process = self.has_previous_process_finished_in_last_day(process_name)
        right_machine = self.is_this_correct_machine(process_name)

        result_dict = dict(
            time_to_start = time_to_start,
            time_to_stop = time_to_stop,
            prev_process = prev_process,
            right_machine = right_machine
        )

        return result_dict

    def has_previous_process_finished_in_last_day(self, process_name):
        previous_process = self.previous_process_name(process_name)
        if previous_process is None:
            return True
        control_process = dataControlProcess(self.data)
        result = control_process.has_process_finished_in_last_day(
            previous_process)

        return result

    def is_it_time_to_run(self, process_name):
        start_time = self.get_start_time(process_name)
        stop_time = self.get_stop_time(process_name)
        now_time = datetime.datetime.now().time()

        if now_time >= start_time and now_time < stop_time:
            return True
        else:
            return False

    def is_this_correct_machine(self, process_name):
        required_host = self.required_machine_name(process_name)
        if required_host is None:
            return True

        hostname = socket.gethostname()

        if hostname == required_host:
            return True
        else:
            return False

    def is_it_time_to_stop(self, process_name):
        stop_time = self.get_stop_time(process_name)
        now_time = datetime.datetime.now().time()

        if now_time > stop_time:
            return True
        else:
            return False

    def run_on_completion_only(self, process_name, method_name):
        this_method_dict = self.get_method_configuration_for_process_name(
            process_name, method_name
        )
        run_on_completion_only = this_method_dict.get(
            "run_on_completion_only", False)
        run_on_completion_only = str2Bool(run_on_completion_only)

        return run_on_completion_only

    def frequency_for_process_and_method(
        self, process_name, method_name
    ):
        frequency, _ = self.frequency_and_max_executions_for_process_and_method(
            process_name, method_name)
        return frequency

    def max_executions_for_process_and_method(
        self, process_name, method_name
    ):
        _, max_executions = self.frequency_and_max_executions_for_process_and_method(
            process_name, method_name)
        return max_executions

    def frequency_and_max_executions_for_process_and_method(
        self, process_name, method_name
    ):
        """

        :param process_name:  str
        :param method_name:  str
        :return: tuple of int: frequency (minutes), max executions
        """

        (
            frequency,
            max_executions,
        ) = self.frequency_and_max_executions_for_process_and_method_process_dict(
            process_name,
            method_name)

        return frequency, max_executions



    def frequency_and_max_executions_for_process_and_method_process_dict(
        self, process_name, method_name
    ):

        this_method_dict = self.get_method_configuration_for_process_name(
            process_name, method_name
        )
        frequency = this_method_dict.get("frequency", 60)
        max_executions = this_method_dict.get("max_executions", 1)

        return frequency, max_executions

    def get_method_configuration_for_process_name(
            self, process_name, method_name):
        all_method_dict = self.get_all_method_dict_for_process_name(
            process_name)
        this_method_dict = all_method_dict.get(method_name, {})

        return this_method_dict

    def get_list_of_methods_for_process_name(self, process_name: str):
        all_method_dict = self.get_all_method_dict_for_process_name(
            process_name)

        return all_method_dict.keys()

    def get_all_method_dict_for_process_name(self, process_name):
        all_method_dict = self.get_configuration_item_for_process_name(
            process_name, "methods", default={}, use_config_default=False
        )

        return all_method_dict

    def previous_process_name(self, process_name):
        """

        :param process_name:
        :return: str or None
        """
        return self.get_configuration_item_for_process_name(
            process_name, "previous_process", default=None, use_config_default=False)

    def get_start_time(self, process_name):
        """
        Return time object, or 00:01 if none available
        :param process_name:
        :return:
        """
        result = self.get_configuration_item_for_process_name(
            process_name, "start_time", default=None, use_config_default=True
        )
        if result is None:
            result = "00:01"

        result = datetime.datetime.strptime(result, "%H:%M").time()

        return result

    def how_long_in_hours_before_trading_process_finishes(self):

        now_datetime = datetime.datetime.now()

        now_date = now_datetime.date()
        stop_time = self.get_stop_time_of_trading_process()
        stop_datetime = datetime.datetime.combine(now_date, stop_time)

        diff = stop_datetime - now_datetime
        time_seconds = max(0, diff.total_seconds())
        time_hours = time_seconds / SECONDS_PER_HOUR

        return time_hours

    def get_stop_time_of_trading_process(self):
        return self.get_stop_time("run_stack_handler")

    def get_stop_time(self, process_name):
        """
        Return time object, or 00:01 if none available
        :param process_name:
        :return:
        """
        result = self.get_configuration_item_for_process_name(
            process_name, "stop_time", default=None, use_config_default=True
        )
        if result is None:
            result = "23:50"

        result = datetime.datetime.strptime(result, "%H:%M").time()

        return result

    def required_machine_name(self, process_name):
        """

        :param process_name:
        :return: str or None
        """
        result = self.get_configuration_item_for_process_name(
            process_name, "host_name", default=None, use_config_default=False
        )

        return result

    def get_configuration_item_for_process_name(
        self, process_name, item_name, default=None, use_config_default=False
    ):
        process_config_for_item = self.get_process_configuration_for_item_name(
            item_name
        )
        config_item = process_config_for_item.get(process_name, default)
        if use_config_default and config_item is default:
            config_item = process_config_for_item.get("default", default)

        return config_item

    def get_process_configuration_for_item_name(self, item_name):
        config = getattr(self, "_process_config_%s" % item_name, None)
        if config is None:
            config = get_key_value_from_dict(
                "process_configuration_%s" % item_name
            )
            if config is missing_data:
                return {}
            setattr(self, "_process_config_%s" % item_name, config)

        return config



    def when_method_last_started(self, process_name: str, method_name: str) -> datetime.datetime:
        result = self.data.db_control_process.when_method_last_started(process_name, method_name)
        return result

    def when_method_last_ended(self, process_name: str, method_name: str) -> datetime.datetime:
        result = self.data.db_control_process.when_method_last_ended(process_name, method_name)
        return result

    def method_currently_running(self, process_name: str, method_name: str) -> bool:
        result = self.data.db_control_process.method_currently_running(process_name, method_name)
        return  result

    def get_control_for_process_name(self, process_name: str):
        result = self.data.db_control_process.get_control_for_process_name(process_name)

        return result

    def get_list_of_process_names(self) -> list:
        result = self.data.db_control_process.get_list_of_process_names()
        return result


def get_key_value_from_dict(item_name):
    config_dict = get_config_dict()

    return config_dict.get(item_name, missing_data)


def get_config_dict() -> dict:
    private_dict = get_private_control_config()
    if private_dict is not missing_data:
        return private_dict
    public_dict = get_public_control_config()
    if public_dict is missing_data:
        raise Exception("Need to have eithier %s or %s present:" % (
        str(PUBLIC_CONTROL_CONFIG_FILE), str(PRIVATE_CONTROL_CONFIG_FILE)))

    return public_dict



def get_public_control_config():
    try:
        with open(PUBLIC_CONTROL_CONFIG_FILE) as file_to_parse:
            config_dict = yaml.load(file_to_parse, Loader=yaml.FullLoader)
    except BaseException:
        config_dict = missing_data

    return config_dict

def get_private_control_config():
    try:
        with open(PRIVATE_CONTROL_CONFIG_FILE) as file_to_parse:
            config_dict = yaml.load(file_to_parse, Loader=yaml.FullLoader)
    except BaseException:
        config_dict = missing_data

    return config_dict


def get_list_of_strategies_for_process(data: dataBlob, process_name: str) -> list:
    diag_config = diagControlProcess(data)
    list_of_strategies = diag_config.get_list_of_methods_for_process_name(process_name)

    return list_of_strategies


def get_strategy_class_object_config(data: dataBlob, process_name: str, strategy_name: str):
    """
    returns dict with
          object: sysproduction.strategy_code.run_system_classic.runSystemClassic
      function: run_system_classic
      backtest_config_filename: systems.provided.futures_chapter15.futures_config.yaml

    """
    diag_config = diagControlProcess(data)
    config_this_process = diag_config.get_method_configuration_for_process_name(process_name, strategy_name)

    return config_this_process