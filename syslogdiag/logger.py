import datetime
from copy import copy
from typing import Union
from syslogdiag.log_entry import LOG_MAPPING, DEFAULT_LOG_MSG_LEVEL, logEntry
from syscore.constants import none_type

ALLOWED_LOG_LEVELS = ["off", "terse", "on"]
DEFAULT_LOG_LEVEL = "off"

SECONDS_BETWEEN_IDENTICAL_LOGS = 60


class logger(object):
    """
    log: used for writing messages

    Messages are datestamped, and tagged with attributes for storage / processing

    This is the base class

    Will also do reporting and emailing of errors


    """

    def __init__(self, type: str, log_level: str = DEFAULT_LOG_LEVEL, **kwargs):
        """
        Base class for logging.

        >>> log=logger("base_system") ## set up a logger with type "base_system"
        >>> log
        Logger (off) attributes- type: base_system
        >>>
        >>> log=logger("another_system", stage="test") ## optionally add other attributes
        >>> log
        Logger (off) attributes- stage: test, type: another_system
        >>>
        >>> log2=logger(log, log_level="on", stage="combForecast") ## creates a copy of log
        >>> log
        Logger (off) attributes- stage: test, type: another_system
        >>> log2
        Logger (on) attributes- stage: combForecast, type: another_system
        >>>
        >>> log3=log2.setup(stage="test2") ## to avoid retyping; will make a copy so attributes aren't kept
        >>> log2
        Logger (on) attributes- stage: combForecast, type: another_system
        >>> log3
        Logger (on) attributes- stage: test2, type: another_system
        >>>
        >>> log3.label(instrument_code="EDOLLAR") ## adds the attribute without making a copy
        >>> log3
        Logger (on) attributes- instrument_code: EDOLLAR, stage: test2, type: another_system
        >>>
        >>>
        """
        self._set_log_attributes(type, kwargs)
        self.set_logging_level(log_level)

    def _set_log_attributes(self, type, kwargs: dict):
        if isinstance(type, str):
            log_attributes = self._get_attributes_given_string(type, kwargs)
        elif hasattr(type, "attributes"):
            log_attributes = self._get_attributes_given_log(type, kwargs)
        else:
            raise Exception(
                "Can only create a logger from another logger, or a str identifier"
            )

        self._attributes = log_attributes

    def _get_attributes_given_string(self, type: str, kwargs: dict) -> dict:
        # been passed a label, so not inheriting anything
        log_attributes = dict(type=type)
        other_attributes = kwargs

        log_attributes = get_update_attributes_list(log_attributes, other_attributes)

        return log_attributes

    def _get_attributes_given_log(self, type, kwargs: dict) -> dict:
        # probably a log
        new_attributes = kwargs
        parent_attributes = type.attributes

        log_attributes = get_update_attributes_list(parent_attributes, new_attributes)

        return log_attributes

    @property
    def attributes(self) -> dict:
        return self._attributes

    @property
    def logging_level(self) -> str:
        return self._log_level

    def set_logging_level(self, new_level: str):
        new_level = new_level.lower()

        if new_level not in ALLOWED_LOG_LEVELS:
            raise Exception(
                "You can't log with level %s must be one of %s",
                (new_level, str(ALLOWED_LOG_LEVELS)),
            )

        self._log_level = new_level

    def __repr__(self):
        attributes = self.attributes
        attr_keys = sorted(attributes.keys())

        attribute_desc = [
            keyname + ": " + str(attributes[keyname]) for keyname in attr_keys
        ]
        return "Logger (%s) attributes- %s" % (
            self.logging_level,
            ", ".join(attribute_desc),
        )

    def setup(self, **kwargs):
        # Create a copy of me with different attributes

        new_log = copy(self)

        log_attributes = new_log.attributes
        passed_attributes = kwargs

        new_attributes = get_update_attributes_list(log_attributes, passed_attributes)

        new_log._attributes = new_attributes

        return new_log

    def label(self, **kwargs):
        # permanently add new attributes to me
        log_attributes = self.attributes
        passed_attributes = kwargs

        new_attributes = get_update_attributes_list(log_attributes, passed_attributes)

        self._attributes = new_attributes

    def msg(self, text: str, **kwargs) -> logEntry:
        msg_level = LOG_MAPPING["msg"]
        return self.log(text, msglevel=msg_level, **kwargs)

    def terse(self, text: str, **kwargs) -> logEntry:
        msg_level = LOG_MAPPING["terse"]
        return self.log(text, msglevel=msg_level, **kwargs)

    def warn(self, text: str, **kwargs) -> logEntry:
        msg_level = LOG_MAPPING["warn"]
        return self.log(text, msglevel=msg_level, **kwargs)

    def error(self, text: str, **kwargs) -> logEntry:
        msg_level = LOG_MAPPING["error"]
        return self.log(text, msglevel=msg_level, **kwargs)

    def critical(self, text: str, **kwargs) -> logEntry:
        msg_level = LOG_MAPPING["critical"]
        return self.log(text, msglevel=msg_level, **kwargs)

    def log(
        self, text: str, msglevel: int = DEFAULT_LOG_MSG_LEVEL, **kwargs
    ) -> Union[logEntry, none_type]:
        log_attributes = self.attributes
        passed_attributes = kwargs

        use_attributes = get_update_attributes_list(log_attributes, passed_attributes)

        same_msg_logged_recently = self._check_msg_logged_recently_or_update_hash(
            text=text, attributes=use_attributes, msglevel=msglevel
        )
        if same_msg_logged_recently:
            ## Don't spam the poor user!
            return None

        log_id = self.get_next_log_id()
        log_result = self.log_handle_caller(
            msglevel=msglevel, text=text, attributes=use_attributes, log_id=log_id
        )

        return log_result

    def _check_msg_logged_recently_or_update_hash(
        self, text: str, msglevel: int, attributes: dict
    ) -> bool:
        msg_hash = "%s %s %d" % (text, str(attributes), msglevel)
        recently_logged = self._msg_hash_logged_recently(msg_hash)
        if recently_logged:
            return True
        else:
            self._update_msg_hash_and_date(msg_hash)
            return False

    def _msg_hash_logged_recently(self, msg_hash: str) -> bool:
        last_hash = self.last_msg_hash
        if not msg_hash == last_hash:
            ## genuinely new
            return False

        seconds_elapsed = self._seconds_since_last_log()
        if seconds_elapsed > SECONDS_BETWEEN_IDENTICAL_LOGS:
            # treat as new
            return False

        ## same hash and recently logged, so...
        return True

    def _seconds_since_last_log(self) -> float:
        ## repeat message but is is stale?
        last_date = self.last_msg_date

        date_diff = datetime.datetime.now() - last_date
        return date_diff.seconds

    def _update_msg_hash_and_date(self, msg_hash: str):
        self.last_msg_hash = msg_hash
        self.last_msg_date = datetime.datetime.now()

    @property
    def last_msg_hash(self):
        return getattr(self, "_last_msg_hash", "")

    @last_msg_hash.setter
    def last_msg_hash(self, msg_hash: str):
        self._last_msg_hash = msg_hash

    @property
    def last_msg_date(self) -> datetime.datetime:
        return getattr(self, "_last_msg_date", datetime.datetime.now())

    @last_msg_date.setter
    def last_msg_date(self, msg_date: datetime.datetime):
        self._last_msg_date = msg_date

    def get_next_log_id(self) -> int:
        """
        Get next log id

        :return: int
        """
        raise NotImplementedError(
            "You need to implement this method in an inherited class or use an inherited claass eg logToMongod"
        )

    def log_handle_caller(
        self, msglevel: int, text: str, attributes: dict, log_id: int
    ):
        raise Exception(
            "You're using a base class for logger - you need to use an inherited class like logtoscreen()"
        )

    """
    Following two methods implement context manager
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def get_update_attributes_list(parent_attributes: dict, new_attributes: dict) -> dict:
    """
    Merge these two dicts together
    """
    return {**parent_attributes, **new_attributes}


class nullLog(logger):
    ## When a log goes to null, does anyone in the forest hear the tree falling?

    ## Overriding these makes the logging faster
    def msg(self, text: str, **kwargs) -> logEntry:
        pass

    def terse(self, text: str, **kwargs) -> logEntry:
        pass

    def warn(self, text: str, **kwargs) -> logEntry:
        pass

    def error(self, text: str, **kwargs) -> logEntry:
        pass

    def critical(self, text: str, **kwargs) -> logEntry:
        pass

    ## These should never be called but just to be on the safe side...
    def log(self, *args, **kwargs):
        pass

    def log_handle_caller(self, *args, **kwargs):

        pass

    def get_next_log_id(self) -> int:
        return 0
