import datetime
from copy import copy

from syscore.dateutils import datetime_to_long, long_to_datetime
from syscore.constants import arg_not_supplied

LOG_MAPPING = dict(msg=0, terse=1, warn=2, error=3, critical=4)
INVERSE_MAP = dict([(value, key) for key, value in LOG_MAPPING.items()])
DEFAULT_LOG_MSG_LEVEL = 0
MSG_LEVEL_DICT = dict(m0="", m1="", m2="[Warning]", m3="[Error]", m4="*CRITICAL*")
LEVEL_ID = (
    "_Level"  # use underscores so less chance of a conflict with labels used by users
)
TIMESTAMP_ID = "_Timestamp"
TEXT_ID = "_Text"
LOG_RECORD_ID = "_Log_Record_id"


class logEntry(object):
    """
    Abstraction for log entries
    """

    def __init__(
        self,
        text: str,
        log_timestamp: datetime.datetime = arg_not_supplied,
        msglevel: int = DEFAULT_LOG_MSG_LEVEL,
        attributes: dict = arg_not_supplied,
        log_id: int = 0,
    ):

        if attributes is arg_not_supplied:
            attributes = {}

        if log_timestamp is arg_not_supplied:
            log_timestamp = datetime.datetime.now()

        use_attributes = copy(attributes)

        self._attributes = use_attributes
        self._text = text
        self._msg_level = msglevel
        self._timestamp = log_timestamp
        self._log_id = log_id

    @classmethod
    def log_entry_from_dict(logEntry, log_dict_input: dict):
        """
        Starting with the dictionary representation, recover the original logEntry

        :param log_dict: dict, as per logEntry.log_dict()
        :return: logEntry object
        """
        log_dict = copy(log_dict_input)
        log_timestamp_aslong = log_dict.pop(TIMESTAMP_ID)
        msg_level = log_dict.pop(LEVEL_ID)
        text = log_dict.pop(TEXT_ID)
        log_id = log_dict.pop(LOG_RECORD_ID)
        attributes = log_dict

        log_timestamp = long_to_datetime(log_timestamp_aslong)

        log_entry = logEntry(
            text,
            log_timestamp=log_timestamp,
            msglevel=msg_level,
            attributes=attributes,
            log_id=log_id,
        )

        return log_entry

    def __repr__(self):
        return "%s %s %s %s" % (
            self.timestamp_as_text,
            str(self.attributes),
            self.msg_level_as_text,
            self.text,
        )

    @property
    def log_id(self) -> int:
        return self._log_id

    def log_as_dict(self) -> dict:
        log_dict = copy(self.attributes)

        log_timestamp_as_long = datetime_to_long(self.timestamp)

        log_dict[LEVEL_ID] = self.msg_level
        log_dict[TIMESTAMP_ID] = log_timestamp_as_long
        log_dict[TEXT_ID] = self.text
        log_dict[LOG_RECORD_ID] = self.log_id

        return log_dict

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def timestamp_as_text(self) -> str:
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def text(self) -> str:
        return self._text

    @property
    def msg_level(self) -> int:
        return self._msg_level

    @property
    def msg_level_as_text(self):
        msglevel = self.msg_level
        msg_level_text = MSG_LEVEL_DICT["m%d" % msglevel]

        return msg_level_text

    @property
    def attributes(self):
        return self._attributes
