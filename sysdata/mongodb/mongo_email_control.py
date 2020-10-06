import datetime
from syscore.dateutils import datetime_to_long, long_to_datetime, ARBITRARY_START
from sysdata.production.email_control import emailControlData
from sysdata.mongodb.mongo_connection import mongoConnection
from syslogdiag.log import logtoscreen

EMAIL_CONTROL_COLLECTION = "EMAIL_CONTROL"
LAST_EMAIL_SENT = "last_email_sent"
LAST_WARNING_SENT = "last_warning_sent"
STORED_MSG = "stored_message"


class mongoEmailControlData(emailControlData):
    def __init__(
            self,
            mongo_db=None,
            log=logtoscreen("mongoEmailControlData")):

        self._mongo = mongoConnection(
            EMAIL_CONTROL_COLLECTION, mongo_db=mongo_db)

        self.name = (
            "simData connection for email control, mongodb %s/%s @ %s -p %s "
            % (
                self._mongo.database_name,
                self._mongo.collection_name,
                self._mongo.host,
                self._mongo.port,
            )
        )
        self.log = log

    def get_time_last_email_sent_with_this_subject(self, subject):
        result_as_datetime = self._get_time_last_email_of_type_sent_with_this_subject(
            subject, LAST_EMAIL_SENT)

        return result_as_datetime

    def get_time_last_warning_email_sent_with_this_subject(self, subject):
        result_as_datetime = self._get_time_last_email_of_type_sent_with_this_subject(
            subject, LAST_WARNING_SENT)

        return result_as_datetime

    def _get_time_last_email_of_type_sent_with_this_subject(
            self, subject, type):
        result_dict = self._mongo.collection.find_one(
            dict(type=type, subject=subject))
        if result_dict is None:
            return ARBITRARY_START
        result = result_dict["datetime"]
        result_as_datetime = long_to_datetime(result)

        return result_as_datetime

    def record_date_of_email_send(self, subject):
        self._record_date_of_email_type_send(subject, type=LAST_EMAIL_SENT)

    def record_date_of_email_warning_send(self, subject):
        self._record_date_of_email_type_send(subject, type=LAST_WARNING_SENT)

    def _record_date_of_email_type_send(self, subject, type):
        datetime_now = datetime_to_long(datetime.datetime.now())
        search_dict = dict(type=type, subject=subject)

        result_dict = self._mongo.collection.find_one(search_dict)
        if result_dict is None:
            object_dict = dict(
                type=type,
                subject=subject,
                datetime=datetime_now)
            self._mongo.collection.insert_one(object_dict)
        else:
            set_dict = {"$set": {"datetime": datetime_now}}
            self._mongo.collection.update_one(search_dict, set_dict)

    def store_message(self, body, subject):
        datetime_now = datetime_to_long(datetime.datetime.now())

        object_dict = dict(
            type=STORED_MSG, subject=subject, datetime=datetime_now, body=body
        )
        self._mongo.collection.insert_one(object_dict)

    def get_stored_messages(self, subject):
        cursor = self._mongo.collection.find(dict(type=STORED_MSG))
        list_of_msg_dicts = [dict for dict in cursor]
        stored_msgs = [
            (long_to_datetime(dict["datetime"]), dict["subject"], dict["body"])
            for dict in list_of_msg_dicts
        ]

        return stored_msgs

    def delete_stored_messages(self, subject=None):
        if subject is None:
            # everything
            self._mongo.collection.remove(dict(type=STORED_MSG))
        else:
            self._mongo.collection.remove(
                dict(type=STORED_MSG, subject=subject))
