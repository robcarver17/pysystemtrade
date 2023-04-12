import logging
from queue import Queue
import atexit
from logging.config import ConvertingList, ConvertingDict, valid_ident
from logging.handlers import QueueHandler, QueueListener
from syslogdiag.emailing import send_mail_msg


def _resolve_handlers(l):
    if not isinstance(l, ConvertingList):
        return l

    # Indexing the list performs the evaluation.
    return [l[i] for i in range(len(l))]


def _resolve_queue(q):
    if not isinstance(q, ConvertingDict):
        return q
    if "__resolved_value__" in q:
        return q["__resolved_value__"]

    cname = q.pop("class")
    klass = q.configurator.resolve(cname)
    props = q.pop(".", None)
    kwargs = {k: q[k] for k in q if valid_ident(k)}
    result = klass(**kwargs)
    if props:
        for name, value in props.items():
            setattr(result, name, value)

    q["__resolved_value__"] = result
    return result


class QueueListenerHandler(QueueHandler):

    # Gratefully stolen from https://github.com/rob-blackbourn/medium-queue-logging

    def __init__(
        self, handlers, respect_handler_level=False, auto_run=True, queue=Queue(-1)
    ):
        queue = _resolve_queue(queue)
        super().__init__(queue)
        handlers = _resolve_handlers(handlers)
        self._listener = QueueListener(
            self.queue, *handlers, respect_handler_level=respect_handler_level
        )
        if auto_run:
            self.start()
            atexit.register(self.stop)

    def start(self):
        print("Starting logging queue listener...")
        self._listener.start()

    def stop(self):
        print("Shutting down logging queue listener\n")
        self._listener.stop()


class PstSMTPHandler(logging.Handler):
    """
    A handler class which sends an SMTP email for each logging event, using the
    existing PST config. Defaults to send emails for CRITICAL records only
    """

    def __init__(self, level=logging.CRITICAL):
        logging.Handler.__init__(self, level=level)

    def emit(self, record):
        try:
            subject_line = f"*{record.levelname}*: {record.msg}"
            send_mail_msg(record.msg, subject_line)
        except Exception as exc:
            print(f"Problem sending message: {exc}")
