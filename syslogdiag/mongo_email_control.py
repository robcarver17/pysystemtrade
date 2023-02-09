import datetime
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


class mongoEmailControlData(emailControlData):
    def __init__(self, mongo_db=None, log=logtoscreen("mongoEmailControlData")):

        super().__init__(log=log)
        self._mongo_data = mongoDataWithMultipleKeys(
            EMAIL_CONTROL_COLLECTION, mongo_db=mongo_db
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

    def store_message(self, body, subject):
        datetime_now = datetime_to_long(datetime.datetime.now())
        data_dict = {BODY_KEY: body}
        dict_of_keys = {
            SUBJECT_KEY: subject,
            TYPE_KEY: STORED_MSG,
            DATE_KEY: datetime_now,
        }

        self.mongo_data.add_data(dict_of_keys=dict_of_keys, data_dict=data_dict)

    def get_stored_messages(self):
        dict_of_keys = {TYPE_KEY: STORED_MSG}
        list_of_msg_dicts = self.mongo_data.get_list_of_result_dicts_for_dict_keys(
            dict_of_keys
        )
        stored_msgs = [
            (long_to_datetime(dict[DATE_KEY]), dict[SUBJECT_KEY], dict[BODY_KEY])
            for dict in list_of_msg_dicts
        ]

        return stored_msgs

    def delete_stored_messages(self):
        # everything
        self.mongo_data.delete_data_without_any_warning({TYPE_KEY: STORED_MSG})
