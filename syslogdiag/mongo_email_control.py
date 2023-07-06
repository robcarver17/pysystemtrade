import datetime
import pymongo
from syscore.dateutils import datetime_to_long, long_to_datetime
from syslogdiag.email_control import emailControlData
from sysdata.mongodb.mongo_generic import mongoDataWithMultipleKeys

from syslogdiag.log_to_screen import logtoscreen

EMAIL_CONTROL_COLLECTION = "EMAIL_CONTROL"
LAST_EMAIL_SENT = "last_email_sent"
LAST_WARNING_SENT = "last_warning_sent"
STORED_MSG = "stored_message"
SUBJECT_KEY = "subject"
BODY_KEY = "body"
TYPE_KEY = "type"
DATE_KEY = "datetime"
INDEX_CONFIG = {
    "keys": {
        TYPE_KEY: pymongo.ASCENDING,
        SUBJECT_KEY: pymongo.ASCENDING,
        DATE_KEY: pymongo.DESCENDING,
    },
    "unique": True,
}


class mongoEmailControlData(emailControlData):
    def __init__(self, mongo_db=None, log=logtoscreen("mongoEmailControlData")):

        super().__init__(log=log)
        self._mongo_data = mongoDataWithMultipleKeys(
            EMAIL_CONTROL_COLLECTION,
            mongo_db=mongo_db,
            index_config=INDEX_CONFIG,
        )

    def __repr__(self):
        return "mongoEmailControlData %s" % str(self.mongo_data)

    @property
    def mongo_data(self):
        return self._mongo_data

    def get_time_last_email_sent_with_this_subject(self, subject):
        result_as_datetime = self._get_time_last_email_of_type_sent_with_this_subject(
            subject, LAST_EMAIL_SENT
        )

        return result_as_datetime

    def get_time_last_warning_email_sent_with_this_subject(self, subject):
        result_as_datetime = self._get_time_last_email_of_type_sent_with_this_subject(
            subject, LAST_WARNING_SENT
        )

        return result_as_datetime

    def _get_time_last_email_of_type_sent_with_this_subject(self, subject, type):
        result_dict = self.mongo_data.get_result_dict_for_dict_keys(
            {TYPE_KEY: type, SUBJECT_KEY: subject}
        )

        result = result_dict[DATE_KEY]
        result_as_datetime = long_to_datetime(result)

        return result_as_datetime

    def record_date_of_email_send(self, subject):

        self._record_date_of_email_type_send(subject, type=LAST_EMAIL_SENT)

    def record_date_of_email_warning_send(self, subject):
        self._record_date_of_email_type_send(subject, type=LAST_WARNING_SENT)

    def _record_date_of_email_type_send(self, subject, type):
        datetime_now = datetime_to_long(datetime.datetime.now())
        data_dict = {DATE_KEY: datetime_now}
        dict_of_keys = {SUBJECT_KEY: subject, TYPE_KEY: type}

        self.mongo_data.add_data(
            dict_of_keys=dict_of_keys, data_dict=data_dict, allow_overwrite=True
        )
