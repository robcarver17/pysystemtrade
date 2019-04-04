# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

# Open a plain text file for reading.  For this example, assume that
# the text file contains only ASCII characters.



def _send_msg(msg):
    """
    Send a message composed by other things

    """

    me = MYEMAIL
    you = MYEMAIL
    msg['From'] = me
    msg['To'] = you

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP(MYSERVER, 25)
    s.login(MYEMAIL, MYPWD)
    s.sendmail(me, [you], msg.as_string())
    s.quit()


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


if __name__ == "__main__":
    send_mail_file("/home/rsc/workspace/systematic_engine/examplecode/eg.txt", "test")
    send_mail_msg("testing", "test subject")
    send_mail_pdfs("testing", ["/home/rsc/Documents/plan view of log store.pdf"], "test subject")
