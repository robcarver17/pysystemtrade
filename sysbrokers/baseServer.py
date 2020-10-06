import queue
import datetime
from syslogdiag.log import logtoscreen
from time import sleep

# marker for when queue is finished
FINISHED = object()
STARTED = object()
TIME_OUT = object()
WAITING = object()


class timer(object):
    def __init__(self, wait_time=0):
        self._start_time = datetime.datetime.now()

        self._wait_time = wait_time

    def elapsed(self):
        current_time = datetime.datetime.now()
        elapsed_time = current_time - self._start_time

        return elapsed_time.total_seconds()

    def finished(self):
        elapsed_time = self.elapsed()
        if elapsed_time > self._wait_time:
            return True
        else:
            return False

    def force_finish(self):
        self._wait_time = 0


class finishableQueue(object):
    def __init__(self, queue_to_finish):
        """

        :param queue_to_finish: a fresh queue object
        """

        self._queue = queue_to_finish
        self.status = STARTED

    def get(self, timeout):
        """
        Returns a list of queue elements once timeout is finished, or a FINISHED flag is received in the queue

        :param timeout: how long to wait before giving up
        :return: list of queue elements
        """
        contents_of_queue = []
        queue_timer = timer(timeout)

        self.status = WAITING
        while not queue_timer.finished():
            try:
                current_element = self._queue.get(block=False)
            except queue.Empty:
                # Wait until something in the queue, or we finish
                continue

            if current_element is FINISHED:
                # We don't put the FINISHED block in the queue, it's just a marker
                # The finished block can sometimes be a red herring, so will
                # keep waiting
                self.status = FINISHED
                break
            else:
                contents_of_queue.append(current_element)
                # keep going and try and get more data

        if self.status is WAITING:
            # Must have run out of time rather than a natural finish
            self.status = TIME_OUT

        return contents_of_queue

    def timed_out(self):
        return self.status is TIME_OUT

    def finished(self):
        return self.status is FINISHED


class brokerServer(object):
    """

    Broker server classes are called by the brokers server application (eg IB Gateway)

    We inherit from this and then write hooks from the servers native methods into the methods in this base class

    The broker_ prefix is used to avoid conflicts with broker objects

    """

    def __init__(self, log=logtoscreen("brokerServer")):
        self.log = log
        self._broker_init_error()

    """
    Error /  message handling code

    The child server object, eg IB, emits errors which are captured by the IB specific error handler
    The error handler decides if this is just a message or an error which might need further action
    It also attaches a set of log kwargs

    Errors / messages are logged

    Errors are also placed on to a queue, so other processes can deal with them

    """

    def _broker_init_error(self):
        error_queue = queue.Queue()
        self._my_errors = error_queue

    def broker_get_error(self, timeout=1):
        if self.broker_is_error():
            try:
                return self._my_errors.get()
            except queue.Empty:
                return None

        return None

    def broker_is_error(self):
        an_error_if = not self._my_errors.empty()
        return an_error_if

    def _broker_add_error_to_queue(
            self,
            errormsg,
            myerror_type="",
            log_tags={}):
        """
        Method called by broker server when an error appears - something that needs action by a process
        myerror_type allows different handlers to be called for different kinds of errors, when built
        for now just put on a big queue

        """
        self._my_errors.put((errormsg, myerror_type, log_tags))

    def broker_message(self, errormsg, log_tags={}):
        """
        Method called by broker server when a warning type of message appears - no action required
        :param errormsg: str
        :param log_tags: dict of tags to pass to log, eg instrument
        :return:
        """
        self.log.msg(errormsg, **log_tags)

    def broker_error(self, errormsg, myerror_type="generic", log_tags={}):
        # Not an 'error' for system purposes, since these cause program
        # termination
        self.log.warn(errormsg, **log_tags)
        self._broker_add_error_to_queue(errormsg, myerror_type, log_tags)
