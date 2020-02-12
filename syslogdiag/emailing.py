import smtplib
import yaml

from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

from syscore.fileutils import get_filename_for_package

PRIVATE_CONFIG_FILE = get_filename_for_package("private.private_config.yaml")



def send_mail_file(textfile, subject):
    """
    Sends an email of a particular text file with subject line

    """

    fp = open(textfile, 'rb')
    # Create a text/plain message
    msg = MIMEText(fp.read())
    fp.close()

    msg['Subject'] = subject

    _send_msg(msg)


def send_mail_msg(body, subject):
    """
    Sends an email of particular text file with subject line

    """

    # Create a text/plain message
    msg = MIMEMultipart()

    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    _send_msg(msg)

def send_mail_pdfs(preamble, filelist, subject):
    """
    Sends an email of files with preamble and subject line

    """

    # Create a text/plain message
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg.preamble = preamble

    for file in filelist:
        fp = open(file, 'rb')
        attach = MIMEApplication(fp.read(), 'pdf')
        fp.close()
        attach.add_header('Content-Disposition', 'attachment', filename='file.pdf')
        msg.attach(attach)

    _send_msg(msg)



def _send_msg(msg):
    """
    Send a message composed by other things

    """

    email_server, email_address, email_pwd = get_email_details()

    me = email_address
    you = email_address
    msg['From'] = me
    msg['To'] = you

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP(email_server, 587)
    s.login(email_address, email_pwd)
    s.sendmail(me, [you], msg.as_string())
    s.quit()


def get_email_details(file_to_parse=PRIVATE_CONFIG_FILE):
    with open(file_to_parse) as file_handle:
        yaml_dict = yaml.load(file_handle)

    email_address = yaml_dict['email_address']
    email_pwd = yaml_dict['email_pwd']
    email_server = yaml_dict['email_server']

    return email_server, email_address, email_pwd



if __name__ == "__main__":
    send_mail_msg("testing", "test subject")
