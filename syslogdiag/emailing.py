from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
import smtplib
from typing import List

import pandas as pd

from sysdata.config.production_config import get_production_config


def send_mail_file(textfile: str, subject: str):
    """
    Sends an email of a particular text file with subject line
    """

    fp = open(textfile, "rb")
    # Create a text/plain message
    msg = MIMEText(fp.read())
    fp.close()

    msg["Subject"] = subject

    _send_msg(msg)


class MailType(Enum):
    plain = "plain"
    html = "html"

    def __str__(self):
        return self.value


def send_mail_msg(body: str, subject: str, mail_type: MailType = MailType.plain):
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg.attach(MIMEText(body, mail_type))
    _send_msg(msg)


def send_mail_dataframe(subject: str, df: pd.DataFrame, header: str = ""):
    df_html = df.to_html()
    html = f"""\
    <html>
    <head>{header}</head>
    <body>
        {df_html}
    </body>
    </html>
    """
    send_mail_msg(html, subject, mail_type=MailType.html)


def send_mail_pdfs(preamble: str, filelist: List[str], subject: str):
    """
    Sends an email of files with preamble and subject line
    """

    # Create a text/plain message
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg.preamble = preamble

    for _file in filelist:
        fp = open(_file, "rb")
        attach = MIMEApplication(fp.read(), "pdf")
        fp.close()
        attach.add_header("Content-Disposition", "attachment", filename="file.pdf")
        msg.attach(attach)

    _send_msg(msg)


def _send_msg(msg: MIMEMultipart):
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
        production_config = get_production_config()
        email_address = production_config.email_address
        email_pwd = production_config.email_pwd
        email_server = production_config.email_server
        email_to = production_config.email_to
        email_port = production_config.email_port
    except:
        raise Exception(
            "Need to have all of these for email to work in private config: email_address, email_pwd, email_server, email_to",
            "email_port",
        )

    return email_server, email_address, email_pwd, email_to, email_port
