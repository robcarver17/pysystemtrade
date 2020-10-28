import datetime
from syscore.dateutils import SECONDS_PER_DAY
from syslogdiag.emailing import send_mail_msg

from sysdata.mongodb.mongo_email_control import mongoEmailControlData

def send_production_mail_msg(data, body, subject, report=False):
    """
    Sends an email of particular text file with subject line
    After checking that we aren't sending too many emails per day

    """
    send_email = can_we_send_this_email_now(data, subject, report=report)

    if send_email:

        try:
            send_mail_msg(body, subject)
            record_date_of_email_send(data, subject)
            return None
        except Exception as e:
            # problem sending emails will store instead
            data.log.msg(
                "Problem %s sending email, will store message instead" % str(e)
            )

    # won't send an email to avoid clogging up the inbox
    # but will send one more to tell the user to check the logs of stored
    # emails
    store_and_warn_email(data, body, subject, report=report)


def can_we_send_this_email_now(data, subject, report=False):
    if report:
        # always send reports
        return True

    last_time_email_sent = get_time_last_email_sent_with_this_subject(
        data, subject)
    sent_in_last_day = check_if_sent_in_last_day(last_time_email_sent)
    if sent_in_last_day:
        return False
    else:
        return True


def store_and_warn_email(data, body, subject, report=False):

    warning_sent = have_we_sent_warning_email_for_this_subject(data, subject)
    if not warning_sent:
        send_warning_email(subject)
        record_date_of_email_warning_send(data, subject)

    store_message(data, body, subject, report=report)


def have_we_sent_warning_email_for_this_subject(data, subject):
    last_time_email_sent = get_time_last_warning_email_sent_with_this_subject(
        data, subject
    )
    result = check_if_sent_in_last_day(last_time_email_sent)

    return result


def check_if_sent_in_last_day(last_time_email_sent):
    time_now = datetime.datetime.now()
    elapsed_time = time_now - last_time_email_sent
    elapsed_time_seconds = elapsed_time.total_seconds()

    if elapsed_time_seconds > SECONDS_PER_DAY:
        # okay to send one email per day, per subject
        return False
    else:
        # too soon
        return True


def send_warning_email(subject):
    send_mail_msg(
        "To reduce email load, won't send any more emails with this subject today. Use interactive_controls, retrieve emails to see stored messages",
        subject,
    )


def get_time_last_email_sent_with_this_subject(data, subject):
    email_control = dataEmailControl(data)
    last_time = email_control.get_time_last_email_sent_with_this_subject(
        subject)
    return last_time


def record_date_of_email_send(data, subject):
    email_control = dataEmailControl(data)
    email_control.record_date_of_email_send(subject)


def get_time_last_warning_email_sent_with_this_subject(data, subject):
    email_control = dataEmailControl(data)
    last_time = email_control.get_time_last_warning_email_sent_with_this_subject(
        subject)
    return last_time


def record_date_of_email_warning_send(data, subject):
    email_control = dataEmailControl(data)
    email_control.record_date_of_email_warning_send(subject)


def store_message(data, body, subject, report=False):
    if report:
        # can't store reports
        return None
    email_control = dataEmailControl(data)
    email_control.store_message(body, subject)


def retrieve_and_delete_stored_messages(data, subject=None):
    """

    :param data: data object
    :param subject: float, or None for everything
    :return: stored messages for printing, in list
    """
    email_control = dataEmailControl(data)
    stored_messages = email_control.get_stored_messages(subject)
    email_control.delete_stored_messages(subject)

    return stored_messages


class dataEmailControl:
    def __init__(self, data):
        # Check data has the right elements to do this
        # uniquely, we don't allow a default data or this causes circular
        # imports
        data.add_class_list([mongoEmailControlData])
        self.data = data

    def get_time_last_email_sent_with_this_subject(self, subject):
        last_time = (
            self.data.db_email_control.get_time_last_email_sent_with_this_subject(
                subject
            )
        )
        return last_time

    def record_date_of_email_send(self, subject):
        self.data.db_email_control.record_date_of_email_send(subject)

    def get_time_last_warning_email_sent_with_this_subject(self, subject):
        last_time = self.data.db_email_control.get_time_last_warning_email_sent_with_this_subject(
            subject)
        return last_time

    def record_date_of_email_warning_send(self, subject):
        self.data.db_email_control.record_date_of_email_warning_send(subject)

    def store_message(self, body, subject):
        self.data.db_email_control.store_message(body, subject)

    def get_stored_messages(self, subject):
        stored = self.data.db_email_control.get_stored_messages(subject)
        return stored

    def delete_stored_messages(self, subject):
        self.data.db_email_control.delete_stored_messages(subject)
