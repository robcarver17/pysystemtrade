from PyPDF2 import PdfMerger
import datetime
import pandas as pd
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from syscore.objects import resolve_function, arg_not_supplied, missing_data
from syscore.objects import header, table, body_text, figure
from syscore.fileutils import get_resolved_pathname
from syscore.dateutils import datetime_to_long
from syscore.text import landing_strip_from_str, landing_strip, centralise_text
from sysdata.data_blob import dataBlob

from syslogdiag.email_via_db_interface import send_production_mail_msg

from sysproduction.reporting.report_configs import reportConfig


def run_report(report_config:
reportConfig, data: dataBlob = arg_not_supplied):
    """

    :param report_config:
    :return:
    """
    pandas_display_for_reports()
    if data is arg_not_supplied:
        data = dataBlob(log_name="Reporting %s" % report_config.title)

    run_report_with_data_blob(report_config, data)


def run_report_with_data_blob(report_config: reportConfig, data: dataBlob):
    """

    :param report_config:
    :return:
    """

    data.log.msg("Running report %s" % str(report_config))
    report_function = resolve_function(report_config.function)
    report_kwargs = report_config.kwargs

    report_results = report_function(data, **report_kwargs)
    parsed_report = parse_report_results(report_results)
    output = report_config.output

    # We either print or email or send to file or ...
    if output == "console":
        print(parsed_report)
    elif output == "email":
        email_report(parsed_report,
                     report_config=report_config, data=data)
    elif output == "file":
        file_report(parsed_report,
                     report_config=report_config, data=data)
    elif output == "emailfile":
        email_report(parsed_report,
                     report_config=report_config, data=data)
        file_report(parsed_report,
                     report_config=report_config, data=data)
    else:
        raise Exception("Report config %s not recognised!" % output)

def email_report(parsed_report,
                 report_config,
                 data):
    send_production_mail_msg(
        data, parsed_report,
        subject=report_config.title,
        email_is_report=True
    )

def file_report(parsed_report,
                 report_config,
                 data):
    filename_with_spaces = report_config.title
    filename = filename_with_spaces.replace(" ", "_")
    write_report_to_file(data, parsed_report, filename=filename)


def parse_report_results(data: dataBlob, report_results: list):
    """
    Parse report results into human readable text for display, email, or christmas present

    :param report_results: list of header, body or table
    :return: String, with more \n than you can shake a stick at
    """

    if report_contains_figures(report_results):
        output_string = parse_report_results_contains_figures(data, report_results)
    else:
        output_string = parse_report_results_contains_text(report_results)

    return output_string

def report_contains_figures(report_results: list) -> bool:
    any_figures_in_report = \
        any([type(report_item) is figure for report_item in report_results])

    return any_figures_in_report

def parse_report_results_contains_text(report_results: list):
    """
    Parse report results into human readable text for display, email, or christmas present

    :param report_results: list of header, body or table
    :return: String, with more \n than you can shake a stick at
    """
    output_string = ""
    for report_item in report_results:
        if isinstance(report_item, header):
            parsed_item = parse_header(report_item)
        elif isinstance(report_item, body_text):
            parsed_item = parse_body(report_item)
        elif isinstance(report_item, table):
            parsed_item = parse_table(report_item)
        else:
            parsed_item = " %s failed to parse in report\n" % str(report_item)

        output_string = output_string + parsed_item

    return output_string


def parse_table(report_table: table) -> str:
    table_header = report_table.Heading
    table_body = str(report_table.Body)
    table_header_centred = centralise_text(table_header, table_body)
    underline_header = landing_strip_from_str(table_header_centred)

    table_string = "\n%s\n%s\n%s\n\n%s\n\n" % (
        underline_header,
        table_header_centred,
        underline_header,
        table_body,
    )

    return table_string


def parse_body(report_body: body_text) -> str:
    body_text = report_body.Text
    return "%s\n" % body_text


def parse_header(report_header: header) -> str:
    header_line = landing_strip(80, "*")
    header_text = centralise_text(report_header.Heading, header_line)

    return "\n%s\n%s\n%s\n\n\n" % (header_line, header_text, header_line)


def parse_report_results_contains_figures(data: dataBlob,
                                          report_results: list) -> str:
    merger = PdfMerger()

    for report_item in report_results:
        if type(report_item) is not figure:
            data.log.critical("Reports can be all figures or all text for now")
            raise Exception()
        pdf = report_item.pdf_filename
        merger.append(pdf)

    merged_filename = _generate_temp_pdf_filename(data)

    merger.write(merged_filename)
    merger.close()

    return merged_filename

def pandas_display_for_reports():
    pd.set_option("display.width", 1000)
    pd.set_option("display.max_columns", 1000)
    pd.set_option("display.max_rows", 1000)


def write_report_to_file(data: dataBlob, parsed_report: str, filename: str):
    use_directory = get_directory_for_reporting(data)
    use_directory_resolved = get_resolved_pathname(use_directory)
    full_filename = os.path.join(use_directory_resolved, filename)
    with open(full_filename, "w") as f:
        f.write(parsed_report)
    data.log.msg("Written report to %s" % full_filename)


def get_directory_for_reporting(data):
    # eg '/home/rob/reports/'
    production_config = data.config
    store_directory = production_config.get_element_or_missing_data(
        "reporting_directory"
    )
    if store_directory is missing_data:
        raise Exception("Need to specify reporting_directory in config file")

    return store_directory

class PdfOutputWithTempFileName():
    """
    # generate some kind of plot, then call:
    pdf_output = PdfOutputWithTempFileName(data)
    figure_object = pdf_output.save_chart_close_and_return_figure()

    """
    def __init__(self, data: dataBlob):
        self._temp_file_name = _generate_temp_pdf_filename(data)

    def save_chart_close_and_return_figure(self) -> figure:
        with PdfPages(self.temp_file_name) as export_pdf:
            export_pdf.savefig()

        plt.close()
        return figure(pdf_filename=self.temp_file_name)

    @property
    def temp_file_name(self) -> str:
        return self._temp_file_name

TEMPFILE_PATTERN = "_tempfile"
def _generate_temp_pdf_filename(data: dataBlob) -> str:
    use_directory = get_directory_for_reporting(data)
    use_directory_resolved = get_resolved_pathname(use_directory)
    filename = "%s_%s.pdf" % (TEMPFILE_PATTERN, str(datetime_to_long(datetime.datetime.now())))
    full_filename = os.path.join(use_directory_resolved, filename)

    return full_filename