"""
General class for 'running' processes

We kick them all off in the crontab at a specific time (midnight is easiest), but their subsequent behaviour will
 depend on various rules, as defined in ... attribute of defaults.yaml or overriden in private_config

- is my process marked as NO OPEN in process control  (check database)
- is it too early for me to run? (defined in .yaml)
- is there a process I am waiting for to finish first?  (defined in .yaml, check database)
- is my process marked as STOP in process control (check database)

- within me, what methods do I call and how often? (defined in child objects)

- is it too late for me to run (definied in .yaml): then I should close down
- what I do when I close down? (defined in child objects)
- how do I mark myself as FINISHED for a subsequent process to know (in database)

"""
import  datetime

from syscore.objects import (arg_not_supplied,
    success,
    failure,
status
)

from syscontrol.timer_functions import get_list_of_timer_functions, listOfTimerFunctions

from sysdata.data_blob import dataBlob

from syslogdiag.log import logtoscreen, logger

from sysobjects.production.process_control import process_no_run, process_running, process_stop

from sysproduction.data.control_process import dataControlProcess, diagControlProcess





LOG_CLEARED = object()
NO_LOG_ENTRY = object()
#FIXME DEBUG
FREQUENCY_TO_CHECK_LOG_MINUTES = 0.2

def _store_name(reason, condition):
    return reason+"/"+condition

def _split_name(keyname):
    return keyname.split("/")

class reportProcessStatus(object):
    ## Report on status when waiting and paused, ensures we don't spam the log
    def __init__(self, log: logger = arg_not_supplied):
        if log is arg_not_supplied:
            log = logtoscreen("")
        self._log = log

    @property
    def log(self):
        return self._log

    def report_wait_condition(self, reason: str, condition_name:str=""):
        we_already_logged_recently = self._have_we_logged_recently(reason, condition_name)

        if we_already_logged_recently:
            return None

        self._log_and_mark_timing(reason, condition_name)

    def clear_all_reasons_for_condition(self, condition_name: str):
        list_of_reasons = self._get_all_reasons_for_condition(condition_name)
        _ = [self.clear_wait_condition(reason, condition_name) for reason in list_of_reasons]

    def clear_wait_condition(self, reason, condition_name:str=""):
        have_we_never_logged_before = self._have_we_never_logged_at_all_before(reason, condition_name)
        if not have_we_never_logged_before:
            # nothing to clear
            return None

        have_we_logged_clear_already = self._have_we_logged_clear_already(reason, condition_name)
        if have_we_logged_clear_already:
            return None
        self._log_clear_and_mark(reason, condition_name)

    def _have_we_logged_recently(self, reason:str, condition_name:str) -> bool:
        last_log_time = self._get_last_log_time(reason, condition_name)
        if last_log_time is NO_LOG_ENTRY:
            return False
        if last_log_time is LOG_CLEARED:
            return False
        time_for_another_log = self._time_for_another_log(last_log_time)
        if time_for_another_log:
            return False
        return True

    def _time_for_another_log(self, log_time):
        elapsed_minutes  =self._minutes_elapsed_since_log(log_time)
        if elapsed_minutes > FREQUENCY_TO_CHECK_LOG_MINUTES:
            return True
        else:
            return False

    def _minutes_elapsed_since_log(self, log_time: datetime.datetime) -> float:
        time_now = datetime.datetime.now()
        elapsed_time = time_now - log_time
        elapsed_seconds = elapsed_time.total_seconds()
        elapsed_minutes = elapsed_seconds/60

        return elapsed_minutes

    def _log_and_mark_timing(self, reason:str, condition_name:str):
        self.log.msg("%s because of %s" % (condition_name, reason))
        self._mark_timing_of_log(reason, condition_name)

    def _mark_timing_of_log(self, reason:str, condition_name:str):
        self._set_last_log_time(reason, condition_name, datetime.datetime.now())

    def _have_we_logged_clear_already(self, reason:str, condition_name:str) -> bool:
        last_log_time = self._get_last_log_time(reason, condition_name)

        return last_log_time is LOG_CLEARED

    def _have_we_never_logged_at_all_before(self, reason:str, condition_name: str) -> bool:
        last_log_time = self._get_last_log_time(reason, condition_name)

        return last_log_time is NO_LOG_ENTRY

    def _get_all_reasons_for_condition(self, condition_name: str):
        paired_keys =  self._get_all_paired_keys_in_store()
        reason_list = [pair[0] for pair in paired_keys if pair[1] == condition_name]

        return reason_list

    def _get_all_paired_keys_in_store(self) -> list:
        all_keys = self._get_all_keys_in_store()
        paired_keys = [_split_name(keyname) for keyname in all_keys]

        return paired_keys

    def _get_all_keys_in_store(self) -> list:
        log_store = self._get_log_store()
        all_keys = list(log_store.keys())

        return all_keys

    def _log_clear_and_mark(self, reason:str, condition_name:str):
        self.log.msg("No longer %s because %s" % (condition_name, reason))
        self._mark_log_of_clear(reason, condition_name)

    def _mark_log_of_clear(self, reason: str, condition_name: str):
        self._set_last_log_time(reason, condition_name, LOG_CLEARED)

    def _get_last_log_time(self, reason:str, condition_name: str) -> datetime.datetime:
        log_store = self._get_log_store()
        log_name = _store_name(reason, condition_name)
        last_log_time = log_store.get(log_name, NO_LOG_ENTRY)

        return last_log_time

    def _set_last_log_time(self, reason:str, condition_name: str, log_time):
        log_store = self._get_log_store()
        log_name = _store_name(reason, condition_name)
        log_store[log_name] = log_time

    def _get_log_store(self) -> dict:
        log_store = getattr(self, "_log_store", None)
        if log_store is None:
            log_store = self._log_store = {}
        return log_store

class processToRun(object):
    """
    Create, then do main_loop
    """

    def __init__(
        self,
        process_name: str,
        data: dataBlob,
        list_of_timer_names_and_functions_as_strings: list
    ):
        self._data = data
        self._process_name = process_name
        self._list_of_timer_functions = get_list_of_timer_functions(
            data,
            process_name,
            list_of_timer_names_and_functions_as_strings
        )

        self._setup()


    @property
    def process_name(self):
        return self._process_name

    @property
    def data(self) -> dataBlob:
        return self._data

    @property
    def list_of_timer_functions(self) -> listOfTimerFunctions:
        return self._list_of_timer_functions

    def _setup(self):
        self._log = self.data.log
        data_control = dataControlProcess(self.data)
        self._data_control = data_control
        diag_process = diagControlProcess(self.data)
        self._diag_process = diag_process

        wait_reporter =reportProcessStatus(self.log)
        self._wait_reporter = wait_reporter

    @property
    def log(self) -> logger:
        return self._log

    @property
    def data_control(self) -> dataControlProcess:
        return self._data_control

    @property
    def diag_process(self) -> diagControlProcess:
        return self._diag_process

    @property
    def wait_reporter(self) -> reportProcessStatus:
        return self._wait_reporter

    def main_loop(self):
        result_of_starting = _start_or_wait(self)
        if result_of_starting is failure:
            return failure

        self._run_on_start()

        is_running = True
        while is_running:
            we_should_stop = _check_for_stop(self)
            if we_should_stop:
                break
            self._do()

        self._finish()

        return success


    def _run_on_start(self):
        self.data_control.start_process(self.process_name)

    def _do(self):
        list_of_timer_functions = self._list_of_timer_functions
        for timer_class in list_of_timer_functions:
            should_pause = check_for_pause_and_log(self)
            if not should_pause:
                timer_class.check_and_run()


    def _finish(self):
        self.list_of_timer_functions.last_run()
        self._finish_control_process()
        self.data.close()


    def _finish_control_process(self):
        result_of_finish = self.data_control.finish_process(self.process_name)

        if result_of_finish is failure:
            self.log.warn(
                "Process %s won't finish in process control as already finished: weird!" %
                self.process_name)
        elif result_of_finish is success:
            self.log.msg(
                "Process control %s marked finished" %
                self.process_name)

### STARTUP CODE

def _start_or_wait(process_to_run: processToRun) -> status:
    waiting = True
    while waiting:
        okay_to_start = _is_okay_to_start(process_to_run)
        if okay_to_start:
            return success

        okay_to_wait = _is_okay_to_wait_before_starting(process_to_run)
        if not okay_to_wait:
            return failure


def _is_okay_to_start(process_to_run: processToRun) -> bool:
    """
    - is my process marked as NO OPEN in process control  (check database): WAIT
    - is it too early for me to run? (defined in .yaml): WAIT
    - is there a process I am waiting for to finish first?  (defined in .yaml, check database): WAIT
    - is my process marked as STOP in process control (check database): DO NOT OPEN

    :return:
    """
    process_status_okay = _check_if_process_status_is_okay_to_run(process_to_run)
    time_to_run = _is_it_time_to_run(process_to_run)
    previous_process_finished = _has_previous_process_finished(process_to_run)

    if process_status_okay and time_to_run and previous_process_finished:
        return True
    else:
        return False


NOT_STARTING_CONDITION =  "Not starting process"

def _check_if_process_status_is_okay_to_run(process_to_run: processToRun) -> bool:
    data_control = process_to_run.data_control
    process_name = process_to_run.process_name
    okay_to_run = data_control.check_if_okay_to_start_process(
        process_name
    )

    wait_reporter = process_to_run.wait_reporter
    if okay_to_run is process_running:
        # already running
        wait_reporter.report_wait_condition("Already running",NOT_STARTING_CONDITION)
        return False

    elif okay_to_run is process_stop:
        wait_reporter.report_wait_condition("Process STOP status", NOT_STARTING_CONDITION)
        return False

    elif okay_to_run is process_no_run:
        wait_reporter.report_wait_condition("Process NO RUN status", NOT_STARTING_CONDITION)
        return False

    elif okay_to_run is success:
        wait_reporter.clear_all_reasons_for_condition(NOT_STARTING_CONDITION)
        return True

    else:
        process_running.log.critical(
            "Process control returned unknown object %s!" %
            str(okay_to_run))

def _is_it_time_to_run(process_to_run: processToRun) -> bool:
    diag_process = process_to_run.diag_process
    process_name = process_to_run.process_name
    time_to_run = diag_process.is_it_time_to_run(process_name)


    TIME_TO_RUN_REASON = "Not yet time to run"
    wait_reporter = process_to_run.wait_reporter

    if time_to_run:
        wait_reporter.clear_wait_condition(TIME_TO_RUN_REASON, NOT_STARTING_CONDITION)
    else:
        wait_reporter.report_wait_condition(TIME_TO_RUN_REASON, NOT_STARTING_CONDITION)

    return  time_to_run

def _has_previous_process_finished(process_to_run: processToRun) -> bool:
    diag_process = process_to_run.diag_process
    process_name = process_to_run.process_name

    other_process_finished = (
        diag_process.has_previous_process_finished_in_last_day(
            process_name
        )
    )
    PREVIOUS_PROCESS_REASON = "Previous process still running"
    wait_reporter = process_to_run.wait_reporter

    if other_process_finished:
        wait_reporter.clear_wait_condition(PREVIOUS_PROCESS_REASON, NOT_STARTING_CONDITION)
    else:
        wait_reporter.report_wait_condition(PREVIOUS_PROCESS_REASON, NOT_STARTING_CONDITION)

    return other_process_finished


def _is_okay_to_wait_before_starting(process_to_run: processToRun):
    """
    - I have run out of time
    - is my process marked as STOP in process control (check database): DO NOT OPEN
    - am I running on the correct machine (defined in .yaml): DO NOT OPEN

    :return: bool: True if okay to wait, False if have to stop waiting
    """

    # check to see if process should have stopped already
    should_have_stopped = _check_for_stop(process_to_run)

    if should_have_stopped:
        # not okay to wait, should have stopped
        return False

    # check to see if process control status means we can't wait
    okay_to_wait = _check_if_okay_to_wait_before_starting_process(process_to_run)

    return okay_to_wait

def _check_if_okay_to_wait_before_starting_process(process_to_run: processToRun) -> bool:
    data_control = process_to_run.data_control
    process_name = process_to_run.process_name

    okay_to_run = data_control.check_if_okay_to_start_process(
        process_name
    )

    log = process_to_run.log
    if okay_to_run is process_running:
        log.warn(
            "Can't start process %s at all since already running"
            % process_name
        )
        return False

    elif okay_to_run is process_stop:
        log.warn(
            "Can't start process %s at all since STOPPED by control"
            % process_name
        )
        return False

    elif okay_to_run is process_no_run:
        # wait in case process changes
        return True

    elif okay_to_run is success:
        # will 'wait' but on next iteration will run
        return True
    else:
        error_msg ="Process control returned unknown object %s!" %\
            str(okay_to_run)
        log.critical(error_msg)
        raise Exception(error_msg)


## PAUSE CODE

def check_for_pause_and_log(process_to_run: processToRun) -> bool:
    data_control = process_to_run.data_control
    should_pause=data_control.check_if_should_pause_process(process_to_run.process_name)

    wait_reporter = process_to_run.wait_reporter
    condition = "Paused running methods"
    reason = "process status is PAUSE"
    if should_pause:
        wait_reporter.report_wait_condition(reason, condition)
    else:
        # clear that we've logged in case we pause again
        wait_reporter.clear_wait_condition(reason, condition)

    return should_pause




## FINISH CODE
def _check_for_stop(process_to_run: processToRun) -> bool:

    """
    - is my process marked as STOP in process control (check database)

    - is it too late for me to run (definied in .yaml): then I should close down
    :return: bool
    """

    process_requires_stop = _check_for_stop_control_process(process_to_run)
    all_methods_finished = _check_if_all_methods_finished(process_to_run)
    time_to_stop = _check_for_finish_time(process_to_run)

    log = process_to_run.log

    if process_requires_stop:
        log.msg("Process control marked as STOP")

    if all_methods_finished:
        log.msg("Finished doing all executions of provided methods")

    if time_to_stop:
        log.msg("Passed finish time of process")

    if process_requires_stop or all_methods_finished or time_to_stop:
        return True
    else:
        return False

def _check_for_stop_control_process(process_to_run: processToRun) -> bool:
    data_control = process_to_run.data_control
    process_name = process_to_run.process_name

    check_for_stop = data_control.check_if_process_status_stopped( process_name
    )

    return check_for_stop

def _check_if_all_methods_finished(process_to_run: processToRun) -> bool:
    list_of_timer_functions = process_to_run.list_of_timer_functions
    check_for_all_methods_finished = list_of_timer_functions.all_finished()


    return check_for_all_methods_finished


def _check_for_finish_time(process_to_run: processToRun) -> bool:
    diag_process = process_to_run.diag_process
    process_name = process_to_run.process_name

    return diag_process.is_it_time_to_stop(process_name)