import argparse
import datetime
import logging
import logging.handlers
import os
import socketserver
import sys
import threading
import time

from syslogging.logger import LOG_FORMAT
from syslogging.handlers import LogRecordStreamHandler, MostRecentHandler
from syslogdiag.log_to_file import get_logging_directory


class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver

    https://code.activestate.com/recipes/577025-loggingwebmonitor-a-central-logging-server-and-mon/
    """

    allow_reuse_address = True
    logname = None

    def __init__(
        self,
        host="localhost",
        port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
        handler=LogRecordStreamHandler,
    ):
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def __repr__(self) -> str:
        return f"{self.server_address[0]}:{self.server_address[1]}"

    def server_activate(self) -> None:
        print(f"{datetime.datetime.now()} Server starting with PID {os.getpid()}")
        super().server_activate()

    def serve_until_stopped(self):
        import select

        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()], [], [], self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort

    def shutdown(self) -> None:
        print(f"\n{datetime.datetime.now()} Server shutting down. Bye")
        super().shutdown()


def logging_server():

    parser = argparse.ArgumentParser(description="Start the socket logging server")
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
        help="listening port",
    )
    parser.add_argument("-f", "--file", help="full path to log file")

    args = parser.parse_args()

    if args.file:
        log_file = args.file
    else:
        log_file = f"{get_logging_directory(None)}/pysystemtrade.log"

    recent = MostRecentHandler()
    recent.setLevel(logging.DEBUG)

    rotating_files = logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        backupCount=5,
        encoding="utf8",
    )
    logging.basicConfig(
        handlers=[recent, rotating_files],
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG,
    )

    socket_receiver = LogRecordSocketReceiver(port=args.port)
    receiver_thread = threading.Thread(target=socket_receiver.serve_forever)
    receiver_thread.daemon = True
    print(
        f"LogRecordSocketReceiver accepting connections at {socket_receiver}, "
        f"writing to '{log_file}', Ctrl-C to shut down"
    )
    receiver_thread.start()

    while True:
        try:
            time.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            socket_receiver.shutdown()
            break

    return 0


if __name__ == "__main__":
    sys.exit(logging_server())
