"""
General class for 'running' processes

We kick them all off in the crontab at a specific time (midnight is easiest), but their subsequent behaviour will
 depend on various rules, as defined in ... attribute of defaults.yaml or overriden in private_config

- is my process marked as NO OPEN in process control  (check database)
- am I running on the correct machine (defined in .yaml)
- is it too early for me to run? (defined in .yaml)
- is there a process I am waiting for to finish first?  (defined in .yaml, check database)
- is my process marked as STOP in process control (check database)

- within me, what methods do I call and how often? (defined in child objects)

- is it too late for me to run (definied in .yaml): then I should close down
- what I do when I close down? (defined in child objects)
- how do I mark myself as FINISHED for a subsequent process to know (in database)

"""
import datetime
from sysproduction.data.controls import dataControlProcess, diagProcessConfig
from syscore.objects import (
    process_no_run,
    process_stop,
    process_running,
    success,
    failure,
    arg_not_supplied,
)
from syslogdiag.echos import redirectOutput
from syslogdiag.log import logtoscreen

DEBUG = True


class processToRun(object):
    """
    Create, then do main_loop
    """

    def __init__(
        self,
        process_name,
        data,
        list_of_timer_names_and_functions,
        use_strategy_config=False,
    ):
        self.data = data
        self._process_name = process_name
        self._setup()
        self._list_of_timer_functions = _get_list_of_timer_functions(
            data,
            process_name,
            list_of_timer_names_and_functions,
            use_strategy_config=use_strategy_config,
        )

    def _setup(self):
        self.log = self.data.log
        data_control = dataControlProcess(self.data)
        self.data_control = data_control
        diag_process = diagProcessConfig(self.data)
        self.diag_process = diag_process
        self._logged_wait_messages = False

    def main_loop(self):
        result_of_starting = self._start_or_wait()
        if result_of_starting is failure:
            return failure

        self._run_on_start()

        if DEBUG:
            is_running = True
            while is_running:
                we_should_stop = self._check_for_stop()
                if we_should_stop:
                    is_running = False
                    break
                self._do()

            self._finish()

        else:
            try:
                is_running = True
                while is_running:
                    we_should_stop = self._check_for_stop()
                    if we_should_stop:
                        is_running = False
                        break
                    self._do()

            except Exception as e:
                self.log.critical(str(e))

            finally:
                self._finish()

        return success

    def _start_or_wait(self):
        waiting = True
        while waiting:
            okay_to_start = self._is_okay_to_start()
            if okay_to_start:
                return success

            okay_to_wait = self._is_okay_to_wait_before_starting()
            if not okay_to_wait:
                return failure

    def _is_okay_to_start(self):
        """
        - is my process marked as NO OPEN in process control  (check database): WAIT
        - am I running on the correct machine (defined in .yaml): DO NOT OPEN
        - is it too early for me to run? (defined in .yaml): WAIT
        - is there a process I am waiting for to finish first?  (defined in .yaml, check database): WAIT
        - is my process marked as STOP in process control (check database): DO NOT OPEN

        :return:
        """
        process_okay = self._check_if_okay_to_start_process()
        correct_machine = self.diag_process.is_this_correct_machine(
            self.process_name)
        time_to_run = self.diag_process.is_it_time_to_run(self.process_name)
        other_process_finished = (
            self.diag_process.has_previous_process_finished_in_last_day(
                self.process_name
            )
        )

        if not self._logged_wait_messages:
            if not time_to_run:
                self.log.msg("Waiting to start as not yet time to run")
            if not other_process_finished:
                self.log.msg("Waiting for previous process to finish first")
            self._logged_wait_messages = True

        if (
            not process_okay
            or not correct_machine
            or not time_to_run
            or not other_process_finished
        ):
            return False

        return True

    def _check_if_okay_to_start_process(self):
        okay_to_run = self.data_control.check_if_okay_to_start_process(
            self.process_name
        )

        if okay_to_run is process_running:
            return False

        elif okay_to_run is process_stop:
            return False

        elif okay_to_run is process_no_run:
            if not self._logged_wait_messages:
                self.log.msg(
                    "Waiting to start as process control set to NO-RUN")
            return False

        elif okay_to_run is success:
            return True
        else:
            self.log.critical(
                "Process control returned unknown object %s!" %
                str(okay_to_run))

    def _is_okay_to_wait_before_starting(self):
        """
        - I have run out of time
        - is my process marked as STOP in process control (check database): DO NOT OPEN
        - am I running on the correct machine (defined in .yaml): DO NOT OPEN

        :return: bool: True if okay to wait, False if have to stop waiting
        """

        # check to see if process should have stopped already
        should_have_stopped = self._check_for_stop()

        if should_have_stopped:
            # not okay to wait, should have stopped
            return False

        correct_machine = self.diag_process.is_this_correct_machine(
            self.process_name)

        if not correct_machine:
            self.log.warn(
                "Can't start process %s as not on correct machine" %
                self.process_name)
            return False

        # check to see if process control status means we can't wait
        process_flag = self._check_if_okay_to_wait_before_starting_process()

        if not process_flag:
            self.log.warn(
                "Can't start process %s because of control process status"
                % self.process_name
            )
            return False

        return True

    def _check_if_okay_to_wait_before_starting_process(self):
        okay_to_run = self.data_control.check_if_okay_to_start_process(
            self.process_name
        )

        if okay_to_run is process_running:
            self.log.warn(
                "Can't start process %s at all since already running"
                % self.process_name
            )
            return False

        elif okay_to_run is process_stop:
            self.log.warn(
                "Can't start process %s at all since STOPPED by control"
                % self.process_name
            )
            return False

        elif okay_to_run is process_no_run:
            # wait in case process changes
            return True

        elif okay_to_run is success:
            return True
        else:
            self.log.critical(
                "Process control returned unknown object %s!" %
                str(okay_to_run))

    def _run_on_start(self):
        self.data_control.start_process(self.process_name)

    def _do(self):
        self._list_of_timer_functions.check_and_run()

    def _check_for_stop(self):
        """
        - is my process marked as STOP in process control (check database)

        - is it too late for me to run (definied in .yaml): then I should close down
        :return: bool
        """

        process_requires_stop = self._check_for_stop_control_process()
        all_methods_finished = self._check_if_all_methods_finished()
        time_to_stop = self._check_for_finish_time()

        if process_requires_stop:
            self.log.msg("Process control marked as STOP")
            return True

        if all_methods_finished:
            self.log.msg("Finished doing all executions of provided methods")
            return True

        if time_to_stop:
            self.log.msg("Passed finish time of process")
            return True

        if process_requires_stop or all_methods_finished or time_to_stop:
            return True

        return False

    def _check_for_stop_control_process(self):
        check_for_stop = self.data_control.check_if_process_status_stopped(
            self.process_name
        )

        return check_for_stop

    def _check_if_all_methods_finished(self):
        check_for_all_methods_finished = self._list_of_timer_functions.all_finished()
        return check_for_all_methods_finished

    def _check_for_finish_time(self):
        return self.diag_process.is_it_time_to_stop(self.process_name)

    def _finish(self):
        self._list_of_timer_functions.last_run()
        self._finish_control_process()
        self.data.close()

        return None

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

        return None

    @property
    def process_name(self):
        return self._process_name


def _get_list_of_timer_functions(
        data,
        process_name,
        list_of_timer_names_and_functions,
        use_strategy_config=False):
    list_of_timer_functions = []
    diag_process = diagProcessConfig(data)
    for entry in list_of_timer_names_and_functions:
        if use_strategy_config:
            strategy_name, object, function_object = entry
            method_name = strategy_name
            run_on_completion_only = False
        else:
            method_name, object = entry
            function_object = getattr(object, method_name)
            run_on_completion_only = diag_process.run_on_completion_only(
                process_name, method_name
            )

        log = object.data.log
        frequency_minutes = diag_process.frequency_for_process_and_method(
            process_name, method_name, use_strategy_config=use_strategy_config
        )
        max_executions = diag_process.max_executions_for_process_and_method(
            process_name, method_name, use_strategy_config=use_strategy_config
        )
        timer_class = timerClassWithFunction(
            method_name,
            function_object,
            frequency_minutes=frequency_minutes,
            max_executions=max_executions,
            run_on_completion_only=run_on_completion_only,
            log=log,
        )
        list_of_timer_functions.append(timer_class)

    list_of_timer_functions = listOfTimerFunctions(list_of_timer_functions)
    return list_of_timer_functions


class listOfTimerFunctions(list):
    def check_and_run(self):
        for timer_class in self:
            timer_class.check_and_run()

    def all_finished(self):
        if len(self) == 0:
            return True

        finished = [timer_class.completed_max_runs() for timer_class in self]
        all_finished = all(finished)

        return all_finished

    def last_run(self):
        for timer_class in self:
            timer_class.check_and_run(last_run=True)


class timerClassWithFunction(object):
    def __init__(
        self,
        name,
        function_to_execute,
        frequency_minutes=60,
        max_executions=1,
        run_on_completion_only=False,
        log=logtoscreen(""),
        minutes_between_heartbeats=10,
    ):
        self._function = function_to_execute  # class.method to run
        self._frequency_minutes = frequency_minutes
        self._max_executions = max_executions
        self._actual_executions = 0
        self._name = name
        self._run_on_completion_only = run_on_completion_only
        self._minutes_between_heartbeats = minutes_between_heartbeats
        self.log = log
        if run_on_completion_only:
            log.msg("%s will run on process completion" % name)
        else:
            log.msg(
                "%s will run every %d minutes at most %d times (-1: infinity)"
                % (name, frequency_minutes, max_executions)
            )

    @property
    def frequency_minutes(self):
        return self._frequency_minutes

    @property
    def name(self):
        return self._name

    @property
    def minutes_between_heartbeats(self):
        return self._minutes_between_heartbeats

    @property
    def run_on_completion_only(self):
        return self._run_on_completion_only

    def check_and_run(self, last_run=False):
        """

        :return: None
        """
        okay_to_run = self.check_if_okay_to_run(last_run=last_run)
        if not okay_to_run:
            return None

        self.run_function()
        self.update_on_run()

        return None

    def check_if_okay_to_run(self, last_run=False):
        if self.run_on_completion_only:
            if last_run:
                self.log_heartbeat()
                self.log.msg(
                    "Running %s as final run for process" %
                    self.name, type=self.name)
                return True
            else:
                return False
        else:
            # normal
            self.log_heartbeat_if_required()

            if last_run:
                # don't run a normal process on last run
                return False
            else:
                # okay not a last run, so check if timer elapsed enough and we
                # haven't done too many
                okay_to_run = self.check_if_ready_for_another_run()
                exceeded_max = self.completed_max_runs()
                if exceeded_max or not okay_to_run:
                    return False
                else:
                    return True

    def check_if_ready_for_another_run(self):
        time_since_run = self.minutes_since_last_run()
        minutes_between_runs = self.frequency_minutes
        if time_since_run > minutes_between_runs:
            return True
        else:
            return False

    def log_heartbeat_if_required(self):

        time_since_run = self.minutes_since_last_heartbeat()
        if time_since_run > self.minutes_between_heartbeats:
            self.log_heartbeat()
        return None

    def log_heartbeat(self):
        self.log.msg(
            "%s still alive, done %d of %d executions every %d minutes"
            % (
                self.name,
                self._actual_executions,
                self._max_executions,
                self.frequency_minutes,
            ),
            type=self.name,
        )
        self._last_heartbeat = datetime.datetime.now()
        return None

    def minutes_since_last_run(self):
        when_last_run = self.when_last_run()
        time_now = datetime.datetime.now()
        delta = time_now - when_last_run
        delta_minutes = delta.total_seconds() / 60.0

        return delta_minutes

    def when_last_run(self):
        when_last_run = getattr(self, "_last_run", None)
        if when_last_run is None:
            when_last_run = datetime.datetime(1970, 1, 1)
            self._last_run = when_last_run

        return when_last_run

    def minutes_since_last_heartbeat(self):
        when_last_beat = self.when_last_heartbeat()
        time_now = datetime.datetime.now()
        delta = time_now - when_last_beat
        delta_minutes = delta.total_seconds() / 60.0

        return delta_minutes

    def when_last_heartbeat(self):
        when_last_heartbeat = getattr(self, "_last_heartbeat", None)
        if when_last_heartbeat is None:
            when_last_heartbeat = datetime.datetime(1970, 1, 1)
            self._last_heartbeat = when_last_heartbeat

        return when_last_heartbeat

    def completed_max_runs(self):
        if self.run_on_completion_only:
            # doesn't apply
            return True
        elif self._max_executions == -1:
            # unlimited
            return False
        elif self._actual_executions >= self._max_executions:
            return True
        else:
            return False

    def run_function(self):
        # Functions can't take args or kwargs or return anything; pure method
        self._function()

    def update_on_run(self):
        self.increment_executions()
        self.set_last_run()
        if self.completed_max_runs():
            self.log.msg(
                "%s executed %d times so done" %
                (self.name, self._max_executions))

    def increment_executions(self):
        self._actual_executions = self._actual_executions + 1

    def set_last_run(self):
        self._last_run = datetime.datetime.now()

        return None
