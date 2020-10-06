class emailControlData(object):
    def get_time_last_email_sent_with_this_subject(self, subject):
        raise NotImplementedError

    def record_date_of_email_send(self, subject):
        raise NotImplementedError

    def get_time_last_warning_email_sent_with_this_subject(self, subject):
        raise NotImplementedError

    def record_date_of_email_warning_send(self, subject):
        raise NotImplementedError

    def store_message(self, body, subject):
        raise NotImplementedError

    def get_stored_messages(self, subject):
        raise NotImplementedError

    def delete_stored_messages(self, subject):
        raise NotImplementedError
