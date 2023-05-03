import argparse
import datetime
import logging
import logging.handlers
import os
import socketserver
import sys

from syslogging.logger import LOG_FORMAT
from syslogging.handlers import LogRecordStreamHandler, MostRecentHandler
from syslogdiag.log_to_file import get_logging_directory


class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver

    https://docs.python.org/3.8/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network
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

    """
    Adapted from:
    https://code.activestate.com/recipes/577025-loggingwebmonitor-a-central-logging-server-and-mon/
    """

    try:
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
            print("WARNING: logs will be writen to current working directory - "
                  "are you sure?")
            log_file = f"{os.getcwd()}/pysystemtrade.log"

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

        with LogRecordSocketReceiver(port=args.port) as server:
            print(
                f"{datetime.datetime.now()} LogRecordSocketReceiver accepting "
                f"connections at {server}, writing to '{log_file}', Ctrl-C to shut down"
            )
            server.serve_forever()

    except KeyboardInterrupt:
        print(
            f"{datetime.datetime.now()} logging_server aborted manually",
            file=sys.stderr,
        )
        return 1

    except Exception as err:
        print(
            f"{datetime.datetime.now()} logging_server problem: {err}", file=sys.stderr
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(logging_server())
