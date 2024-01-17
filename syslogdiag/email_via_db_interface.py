import os
import datetime

from syscore.dateutils import SECONDS_PER_DAY
from syscore.exceptions import missingData
from syslogdiag.mongo_email_control import mongoEmailControlData

from syslogdiag.emailing import send_mail_msg, send_mail_pdfs

from syscore.fileutils import resolve_path_and_filename_for_package
from syscore.interactive.display import landing_strip


def send_production_mail_msg_attachment(body: str, subject: str, filename: str):
    """
    Doesn't check, doesn't store
    """

    send_mail_pdfs(body, subject=subject, filelist=[filename])


def send_production_mail_msg(data, body: str, subject: str, email_is_report=False):
    """
    Sends an email of particular text file with subject line
    After checking that we aren't sending too many emails per day

    """
    send_email = can_we_send_this_email_now(
        data, subject, email_is_report=email_is_report
    )

    if send_email:
        send_email_and_record_date_or_store_on_fail(
            data, body, subject, email_is_report=email_is_report
        )
    else:
        # won't send an email to avoid clogging up the inbox
        # but might send one more to tell the user to check the logs of stored
        # emails
        store_and_warn_email(data, body, subject, email_is_report=email_is_report)


def send_email_and_record_date_or_store_on_fail(
    data, body: str, subject: str, email_is_report: bool = False
):
    try:
        send_mail_msg(body, subject)
        record_date_of_email_send(data, subject)
        data.log.debug("Sent email subject %s" % subject)
    except Exception as e:
        # problem sending emails will store instead
        data.log.debug(
            "Problem %s sending email subject %s, but message will be stored"
            % (str(e), subject)
        )
    store_message(data, body, subject, email_is_report=email_is_report)


def can_we_send_this_email_now(data, subject, email_is_report=False):
    if email_is_report:
        # always send reports
        return True

    try:
        last_time_email_sent = get_time_last_email_sent_with_this_subject(data, subject)
    except missingData:
        return True

    email_was_sent_in_last_day = check_if_sent_in_last_day(last_time_email_sent)

    if email_was_sent_in_last_day:
        return False
    else:
        return True


def store_and_warn_email(data, body, subject, email_is_report=False):
    warning_sent = have_we_sent_warning_email_for_this_subject(data, subject)
    if not warning_sent:
        send_warning_email(data, subject)
        record_date_of_email_warning_send(data, subject)

    store_message(data, body, subject, email_is_report=email_is_report)


def have_we_sent_warning_email_for_this_subject(data, subject):
    try:
        last_time_email_sent = get_time_last_warning_email_sent_with_this_subject(
            data, subject
        )
    except missingData:
        return False

    result = check_if_sent_in_last_day(last_time_email_sent)

    return result


def check_if_sent_in_last_day(last_time_email_sent: datetime.datetime):
    time_now = datetime.datetime.now()
    elapsed_time = time_now - last_time_email_sent
    elapsed_time_seconds = elapsed_time.total_seconds()

    if elapsed_time_seconds > SECONDS_PER_DAY:
        # okay to send one email per day, per subject
        return False
    else:
        # too soon
        return True


def send_warning_email(data, subject):
    body = "To reduce email load, won't send any more emails with this subject today. Use 'interactive_diagnostics', 'Emails' to see stored messages"
    send_email_and_record_date_or_store_on_fail(data, body, subject)


def get_time_last_email_sent_with_this_subject(data, subject):
    email_control = dataEmailControl(data)
    last_time = email_control.get_time_last_email_sent_with_this_subject(subject)
    return last_time


def record_date_of_email_send(data, subject):
    email_control = dataEmailControl(data)
    email_control.record_date_of_email_send(subject)


def get_time_last_warning_email_sent_with_this_subject(data, subject):
    email_control = dataEmailControl(data)
    last_time = email_control.get_time_last_warning_email_sent_with_this_subject(
        subject
    )
    return last_time


def record_date_of_email_warning_send(data, subject):
    email_control = dataEmailControl(data)
    email_control.record_date_of_email_warning_send(subject)


def store_message(data, body, subject, email_is_report=False):
    if email_is_report:
        data.log.debug("Message not stored: can't store reports")
        return None

    email_store_file = get_storage_filename(data)
    with open(email_store_file, "a") as file:
        email_subject_and_date_line = "Email stored not sent on %s: %s" % (
            datetime.datetime.now(),
            subject,
        )
        file.write(landing_strip(80))
        file.write("\n" + email_subject_and_date_line + "\n\n")
        file.write(body + "\n")
        file.write(landing_strip(80) + "\n\n")


def retrieve_and_delete_stored_messages(data) -> str:
    email_store_file = get_storage_filename(data)
    try:
        with open(email_store_file, "r") as file:
            stored_messages = file.read()
        os.remove(email_store_file)
    except FileNotFoundError:
        ## no stored messages
        return "\nNo stored emails\n"

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
            subject
        )
        return last_time

    def record_date_of_email_warning_send(self, subject):
        self.data.db_email_control.record_date_of_email_warning_send(subject)


def get_storage_filename(data: "dataBlob"):
    config = data.config
    email_store_filename = config.get_element_or_default("email_store_filename", None)
    if email_store_filename is None:
        ## Can't log this but print anyway
        print(
            "*** email_store_filename undefined in private_config.yaml, will store in email.log in arbitrary directory"
        )
        return "email.log"

    ## NOTE doesn't create directory
    email_store_filename = resolve_path_and_filename_for_package(email_store_filename)

    return email_store_filename
