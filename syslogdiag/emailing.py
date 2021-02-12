import smtplib

from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

from sysdata.config.private_config import get_private_config


def send_mail_file(textfile, subject):
    """
    Sends an email of a particular text file with subject line

    """

    fp = open(textfile, "rb")
    # Create a text/plain message
    msg = MIMEText(fp.read())
    fp.close()

    msg["Subject"] = subject

    _send_msg(msg)


def send_mail_msg(body, subject):
    """
    Sends an email of particular text file with subject line

    """

    # Create a text/plain message
    msg = MIMEMultipart()

    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    _send_msg(msg)


def send_mail_pdfs(preamble, filelist, subject):
    """
    Sends an email of files with preamble and subject line

    """

    # Create a text/plain message
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg.preamble = preamble

    for file in filelist:
        fp = open(file, "rb")
        attach = MIMEApplication(fp.read(), "pdf")
        fp.close()
        attach.add_header(
            "Content-Disposition",
            "attachment",
            filename="file.pdf")
        msg.attach(attach)

    _send_msg(msg)


def _send_msg(msg):
    """
    Send a message composed by other things

    """

    email_server, email_address, email_pwd, email_to, email_port = get_email_details()

    me = email_address
    you = email_to
    msg["From"] = me
    msg["To"] = you

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP(email_server, email_port)
    # add tls for those using yahoo or gmail. 
    try:
        s.starttls()
    except:
        pass
    s.login(email_address, email_pwd)
    s.sendmail(me, [you], msg.as_string())
    s.quit()


def get_email_details():
    # FIXME DON'T LIKE RETURNING ALL THESE VALUES - return CONFIG or subset?
    try:
        config = get_private_config()
        email_address = config.email_address
        email_pwd = config.email_pwd
        email_server = config.email_server
        email_to = config.email_to
        email_port = config.email_port
    except:
        raise Exception("Need to have all of these for email to work in private config: email_address, email_pwd, email_server, email_to", "email_port")

    return email_server, email_address, email_pwd, email_to, email_port
