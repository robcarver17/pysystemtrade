from syslogdiag.emailing import send_mail_msg

def send_production_mail_msg(data, body, subject, report = False):
    """
    Sends an email of particular text file with subject line

    """

    send_mail_msg(body, subject)