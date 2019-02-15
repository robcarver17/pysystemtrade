import queue

## marker for when queue is finished
FINISHED = object()
STARTED = object()
TIME_OUT = object()

class finishableQueue(object):

    def __init__(self, queue_to_finish):

        self._queue = queue_to_finish
        self.status = STARTED

    def get(self, timeout):
        """
        Returns a list of queue elements once timeout is finished, or a FINISHED flag is received in the queue
        :param timeout: how long to wait before giving up
        :return: list of queue elements
        """
        contents_of_queue=[]
        finished=False

        while not finished:
            try:
                current_element = self._queue.get(timeout=timeout)
                if current_element is FINISHED:
                    finished = True
                    self.status = FINISHED
                else:
                    contents_of_queue.append(current_element)
                    ## keep going and try and get more data

            except queue.Empty:
                ## If we hit a time out it's most probable we're not getting a finished element any time soon
                ## give up and return what we have
                finished = True
                self.status = TIME_OUT


        return contents_of_queue

    def timed_out(self):
        return self.status is TIME_OUT


class brokerServer(object):
    """

    Broker server classes are called by the brokers server application (eg IB Gateway)

    We inherit from this and then write hooks from the servers native methods into the methods in this base class

    The broker_ prefix is used to avoid conflicts with broker objects
    """

    ## error handling code
    def broker_init_error(self):
        error_queue=queue.Queue()
        self._my_errors = error_queue

    def broker_get_error(self, timeout=5):
        if self.broker_is_error():
            try:
                return self._my_errors.get(timeout=timeout)
            except queue.Empty:
                return None

        return None

    def broker_is_error(self):
        an_error_if=not self._my_errors.empty()
        return an_error_if

    def broker_error(self, errormsg):
        """
        Method called by broker server when an error appears

        WHITELIST?
        """
        self._my_errors.put(errormsg)

