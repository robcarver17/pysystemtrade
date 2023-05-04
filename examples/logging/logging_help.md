# Notes for switch to Python logging

(To be merged into docs once changeover done)

## Usage

```
from syslogging.logger import *

# set up a logger with a name
log = get_logger("my_logger")

# create a log message with a logging level
log.debug("debug message")
log.info("info message")
log.warning("warning message")
log.error("error message")
log.critical("critical message")

# parameterise the message
log.info("Hello %s", "world")
log.info("Goodbye %s %s", "cruel", "world")

# setting attributes on initialisation
log = get_logger("attributes", {"stage": "first"})

# setting attributes on message creation
log.info("logging call attributes", instrument_code="GOLD")
```

See [the POC](example/logging/poc.py) for more usage examples, and the [Python
docs](https://docs.python.org/3.8/library/logging.html) for more general info.

## Configuration

By default, log messages will print out to the console (`std.out`) at level DEBUG. This what you get in sim. This is configured by function `_configure_sim()` in `syslogging.logger.py`.

If you want to change the level, or the format of the messages, then create an environment variable that points to an alternative YAML logging configuration. Something like this for Bash

```
PYSYS_LOGGING_CONFIG=/home/path/to/your/logging_config.yaml
```

It could be a file within the project, so will accept the relative dotted path format. There's an example YAML file that replicates the default sim configuration

```
PYSYS_LOGGING_CONFIG=syslogging.logging_sim.yaml
```

## Production

In production, the requirements are more complex. As well as the context relevant attributes (that we have with sim), we also need
- ability to log to the same file from different processes
- output to console for echo files
- critical level messages to trigger an email

Configure the default production setup with:

```
PYSYS_LOGGING_CONFIG=syslogging.logging_prod.yaml
```

At the client side, (pysystemtrade) there are three handlers: socket, console, and email. There is a server (separate process) for the socket handler. More details on each below

### socket

Python doesn't support more than one process writing to a file at the same time. So, on the client side, log messages are serialised and sent over the wire. A simple TCP socket server receives, de-serialises, and writes them to disk. The socket server needs to be running first. The simplest way to start it:

```
python -u $PYSYS_CODE/syslogging/server.py
```

But that would write logs to the current working directory. Probably not what you want. Instead, pass the log file path 

```
python -u $PYSYS_CODE/syslogging/server.py --file /home/path/to/your/pysystemtrade.log
```

By default, the server accepts connections on port 6020. But if you want to use another

```
python -u $PYSYS_CODE/syslogging/server.py --port 6021 --file /home/path/to/your/pysystemtrade.log
```

The server needs to be running all the time. It needs to run in the background, start up on reboot, restart automatically in case of failure, etc. So a better way to do it would be to make it a service

#### socket server as a service

There is an example Linux systemd service file provided, see `examples/logging/logging_server.service`. And a setup guide [here](https://tecadmin.net/setup-autorun-python-script-using-systemd/). Basic setup for Debian/Ubuntu is:

- create a new file at `/etc/systemd/system/logging_server.service`
- paste the example file into it
- update the paths in `ExecStart`. If using a virtual environment, make sure to use the correct path to Python 
- update the `User` and `Group` values, so the log file is not owned by root
- update the path in `Environment`, if using a custom private config directory
- run the following commands to start/stop/restart etc

```
# reload daemon
sudo systemctl daemon-reload

# enable service (restart on boot)
sudo systemctl enable log_server.service

# view service status
sudo systemctl status log_server.service 

# start service
sudo systemctl start log_server.service

# stop service
sudo systemctl stop log_server.service

# restart
sudo systemctl restart log_server.service

# view service log (not pysystemtrade log)
sudo journalctl -e -u log_server.service
```

### console

All log messages also get sent to console, as with sim. The supplied `crontab` entries would therefore also pipe their output to the echo files

### email

There is a special SMTP handler, for CRITICAL log messages only. This handler uses the configured pysystemtrade email settings to send those messages as emails
