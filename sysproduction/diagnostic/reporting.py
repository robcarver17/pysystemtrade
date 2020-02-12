
import pandas as pd

from syscore.objects import  resolve_function, success
from syscore.objects import header, table, body_text

from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob

from syslogdiag.log import logToMongod as logger
from syslogdiag.emailing import send_mail_msg


pd.set_option('display.width', 1000)
pd.set_option('display.max_columns', 1000)
pd.set_option('display.max_rows', 1000)



def run_report(report_config, **kwargs):

    """

    :param report_config:
    :return:
    """
    """
    mongo_db=mongoDb()
    log=logger("Reporting", mongo_db=mongo_db)
    data = dataBlob(mongo_db = mongo_db, log = log)

    """
    with mongoDb() as mongo_db,\
        logger("Reporting", mongo_db=mongo_db) as log:

        data = dataBlob(mongo_db = mongo_db, log = log)

        report_function = resolve_function(report_config.function)

        try:
            report_results = report_function(data, **kwargs)
        except Exception as e:
            report_results = [header("Report %s failed to process with error %s" % (report_config.title, e))]

        try:
            parsed_report = parse_report_results(report_results)
        except Exception as e:
            parsed_report = "Report failed to parse %s with error %s\n" % (report_config.title, str(e))

        # We eithier print or email
        if report_config.output is "console":
            print(parsed_report)
        elif report_config.output is "email":
            send_mail_msg(parsed_report, subject = report_config.title)

        return success

def parse_report_results(report_results):
    """
    Parse report results into human readable text for display, email, or christmas present

    :param report_results: list of header, body or table
    :return: String, with more \n than you can shake a stick at
    """
    output_string = ""
    for report_item in report_results:
        if type(report_item) is header:
            parsed_item = parse_header(report_item)
        elif type(report_item) is body_text:
            parsed_item = parse_body(report_item)
        elif type(report_item) is table:
            parsed_item = parse_table(report_item)
        else:
            parsed_item = " %s failed to parse in report\n" % str(report_item)

        output_string = output_string+parsed_item

    return output_string

def parse_table(report_table):
    table_header = report_table.Heading
    table_body = str(report_table.Body)
    table_header_centred = centralise_text(table_header, table_body)
    underline_header = landing_strip_from_str(table_header_centred)

    table_string = "\n%s\n%s\n%s\n\n%s\n\n" % (underline_header, table_header_centred, underline_header, table_body)

    return table_string

def parse_body(report_body):
    body_text = report_body.Text
    return "%s\n" % body_text

def parse_header(report_header):
    header_line = landing_strip(80, "*")
    header_text = centralise_text(report_header.Heading, header_line)

    return "\n%s\n%s\n%s\n\n\n" % (header_line, header_text, header_line)

def landing_strip_from_str(str_to_match, strip="="):
    str_width = measure_width(str_to_match)
    return landing_strip(width=str_width, strip=strip)

def landing_strip(width=80, strip="*"):
    return strip*width

def centralise_text(text, str_to_match, pad_with=" "):
    match_len = measure_width(str_to_match)
    text_len = len(text)
    if text_len >= match_len:
        return text
    pad_left = int((match_len-text_len)/2.0)
    pad_right = match_len - pad_left - text_len
    pad_left_text = pad_with*pad_left
    pad_right_text = pad_with*pad_right

    new_text = "%s%s%s" % (pad_left_text, text, pad_right_text)

    return new_text

def measure_width(text):
    first_cr = text.find("\n")
    if first_cr==-1:
        first_cr= len(text)

    return first_cr

