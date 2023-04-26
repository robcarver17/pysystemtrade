import os
import sys
import socket
import logging.config
import syslogging
from syslogging.adapter import *
from syslogging.pyyaml_env import parse_config
from syscore.fileutils import resolve_path_and_filename_for_package

CONFIG_ENV_VAR = "PYSYS_LOGGING_CONFIG"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def get_logger(name, attributes=None):
    if not syslogging.logging_configured:
        _configure_logging()
    if name is None or name == "":
        if attributes is not None and "type" in attributes:
            name = attributes["type"]
    return DynamicAttributeLogger(logging.getLogger(name), attributes)


def logtoscreen(name="", **kwargs):
    warnings.warn(
        "The 'logtoscreen' class is deprecated, "
        "use get_logger() from syslogging.logger instead",
        DeprecationWarning,
        2,
    )
    if name is None or name == "":
        if "type" in kwargs:
            name = kwargs["type"]
    return get_logger(name, kwargs)


def nullLog(name):
    warnings.warn(
        "The 'nullLog' class is deprecated, "
        "use get_logger() from syslogging.logger instead",
        DeprecationWarning,
        2,
    )
    return get_logger(name)


def logToFile(name, data):
    warnings.warn(
        "The 'logToFile' class is deprecated, "
        "use get_logger() from syslogging.logger instead",
        DeprecationWarning,
        2,
    )
    return get_logger(name)


def _configure_logging():
    logging_config_path = os.getenv(CONFIG_ENV_VAR, None)
    if logging_config_path:
        _configure_prod(logging_config_path)
    else:
        _configure_sim()


def _configure_sim():
    print(f"Configuring sim logging")
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.DEBUG)
    logging.getLogger("ib_insync").setLevel(logging.WARNING)
    logging.getLogger("arctic").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.INFO)
    logging.basicConfig(
        handlers=[handler],
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG,
    )
    syslogging.logging_configured = True


def _configure_prod(logging_config_file):
    print(f"Attempting to configure prod logging from {logging_config_file}")
    config_path = resolve_path_and_filename_for_package(logging_config_file)
    if os.path.exists(config_path):
        try:
            config = parse_config(path=config_path)
            host, port = _get_log_server_config(config)
            try:
                _check_log_server(host, port)
            except BlockingIOError:
                print(f"Log server detected OK at {host}:{port}")
            except (ConnectionResetError, ConnectionRefusedError):
                print(f"Cannot connect to log server at {host}:{port}, is it running?")
                raise
            logging.config.dictConfig(config)
            syslogging.logging_configured = True
        except Exception as exc:
            print(f"ERROR: Problem configuring prod logging, reverting to sim: {exc}")
            _configure_sim()
    else:
        print(f"ERROR: prod logging config '{config_path}' not found, reverting to sim")
        _configure_sim()


def _get_log_server_config(config):
    handler = config["handlers"]["socket"]
    return handler["host"], handler["port"]


def _check_log_server(host, port):
    # https://stackoverflow.com/questions/48024720/python-how-to-check-if-socket-is-still-connected
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    # this will try to read bytes without blocking and also without removing them
    # from buffer (peek only). If a BlockingIOError is raised, we know the socket
    # is open
    data = sock.recv(16, socket.MSG_DONTWAIT | socket.MSG_PEEK)
    if len(data) == 0:
        raise Exception("Unexpected data length")
