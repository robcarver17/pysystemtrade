import datetime
import itertools

from syscore.constants import arg_not_supplied
from syscore.exceptions import missingData
from sysdata.base_data import baseData
from syslogdiag.logger import logger, DEFAULT_LOG_LEVEL
from syslogdiag.log_entry import INVERSE_MAP, LEVEL_ID, logEntry
from syslogdiag.log_to_screen import logtoscreen

from syslogdiag.email_via_db_interface import send_production_mail_msg

LOG_COLLECTION_NAME = "Logs"
EMAIL_ON_LOG_LEVEL = [4]


class logData(baseData):
    def __init__(self, log: logger = logtoscreen("logData")):
        super().__init__(log=log)

    def delete_log_items_from_before_n_days(self, lookback_days: int = 365):
        # need something to delete old log records, eg more than x months ago

        raise NotImplementedError
