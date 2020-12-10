import datetime

from sysproduction.data.control_process import diagControlProcess, dataControlProcess
from syslogdiag.log import logtoscreen


def _get_list_of_timer_functions(
        data,
        process_name,
        list_of_timer_names_and_functions):
    list_of_timer_functions = []
    diag_process = diagControlProcess(data)

    for entry in list_of_timer_names_and_functions:
        method_name, object = entry
        function_object = getattr(object, method_name)

        run_on_completion_only = diag_process.run_on_completion_only(
            process_name, method_name
        )

        log = object.data.log
        frequency_minutes = diag_process.frequency_for_process_and_method(
            process_name, method_name
        )
        max_executions = diag_process.max_executions_for_process_and_method(
            process_name, method_name
        )
        timer_class = timerClassWithFunction(
            method_name,
            function_object,
            data,
            process_name = process_name,
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
        data,
        process_name:str = "",
        frequency_minutes: int=60,
        max_executions: int=1,
        run_on_completion_only: bool=False,
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
        self._log = log
        self._data = data
        self._process_name = process_name

        if run_on_completion_only:
            log.msg("%s will run on process completion" % name)
        else:
            log.msg(
                "%s will run every %d minutes at most %d times (-1: infinity)"
                % (name, frequency_minutes, max_executions)
            )
    @property
    def data(self):
        return self._data

    @property
    def process_name(self):
        return self._process_name

    @property
    def log(self):
        return self._log

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

        self.log_run_start_method()
        self.update_on_start_run()
        self.run_function()
        self.log_run_end_method()

        return None

    def check_if_okay_to_run(self, last_run=False):
        if self.run_on_completion_only:
            if last_run:
                self.log_heartbeat()
                self.log.msg(
                    "Running %s as final run for process %s" %
                    (self.name, self.process_name), type=self.name)
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

    def update_on_start_run(self):
        self.increment_executions()
        self.set_time_of_last_run()
        if self.completed_max_runs():
            self.log.msg(
                "%s executed %d times so done" %
                (self.name, self._max_executions))


    def increment_executions(self):
        self._actual_executions = self._actual_executions + 1

    def set_time_of_last_run(self):
        self._last_run = datetime.datetime.now()

        return None

    def log_run_start_method(self):
        data_process = dataControlProcess(self.data)
        data_process.log_start_run_for_method(self.process_name, self.name)

    def run_function(self):
        # Functions can't take args or kwargs or return anything; pure method
        self._function()


    def log_run_end_method(self):
        data_process = dataControlProcess(self.data)
        data_process.log_end_run_for_method(self.process_name, self.name)