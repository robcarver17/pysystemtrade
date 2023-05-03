import logging
from collections import deque
import pickle
import socketserver
import struct
from syslogdiag.emailing import send_mail_msg


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


class MostRecentHandler(logging.Handler):
    """
    A Handler which keeps the most recent logging records in memory

    https://code.activestate.com/recipes/577025-loggingwebmonitor-a-central-logging-server-and-mon/
    """

    def __init__(self, max_records=200):
        logging.Handler.__init__(self)
        self.log_records_total = 0
        self.max_records = max_records
        self.db = deque([], max_records)

    def emit(self, record):
        self.log_records_total += 1
        try:
            self.db.append(record)
        except Exception:
            self.handleError(record)


class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    """
    Handler for a streaming logging request.

    This basically logs the record using whatever logging policy is configured locally.

    https://docs.python.org/3.8/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network
    """

    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack(">L", chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = self._unpickle(chunk)
            record = logging.makeLogRecord(obj)
            self._handle_log_record(record)

    def _unpickle(self, data):
        return pickle.loads(data)

    def _handle_log_record(self, record):
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)
