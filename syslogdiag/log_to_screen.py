from syslogdiag.logger import logger
from syslogdiag.log_entry import logEntry


class logtoscreen(logger):
    def log_handle_caller(
        self, msglevel: int, text: str, attributes: dict, log_id: int
    ):
        """
        >>> log=logtoscreen("base_system", log_level="off") ## this won't do anything
        >>> log.log("this wont print")
        >>> log.terse("nor this")
        >>> log.warn("this will")
        this will
        >>> log.error("and this")
        and this
        >>> log=logtoscreen(log, log_level="terse")
        >>> log.msg("this wont print")
        >>> log.terse("this will")
        this will
        >>> log=logtoscreen("",log_level="on")
        >>> log.msg("now prints every little thing")
        now prints every little thing
        """
        log_level = self.logging_level

        log_entry = logEntry(
            text, msglevel=msglevel, attributes=attributes, log_id=log_id
        )

        if msglevel == 0:
            if log_level == "on":
                print(log_entry)
                # otherwise do nothing - either terse or off

        elif msglevel == 1:
            if log_level in ["on", "terse"]:
                print(log_entry)
                # otherwise do nothing - either terse or off

        elif msglevel == 2:
            print(log_entry)

        elif msglevel == 3:
            print(log_entry)

        elif msglevel == 4:
            raise Exception(log_entry)

    def get_next_log_id(self) -> int:
        last_id = self.get_last_used_log_id()
        next_id = last_id + 1

        self.update_log_id(next_id)

        return next_id

    def get_last_used_log_id(self):
        return getattr(self, "_log_id", 0)

    def update_log_id(self, log_id):
        self._log_id = log_id
