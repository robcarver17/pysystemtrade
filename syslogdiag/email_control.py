from sysdata.base_data import baseData
from syslogging.logger import get_logger


class emailControlData(baseData):
    def __init__(self, log=get_logger("email-control-data")):
        super().__init__(log=log)

    def get_time_last_email_sent_with_this_subject(self, subject):
        raise NotImplementedError

    def record_date_of_email_send(self, subject):
        raise NotImplementedError

    def get_time_last_warning_email_sent_with_this_subject(self, subject):
        raise NotImplementedError

    def record_date_of_email_warning_send(self, subject):
        raise NotImplementedError
