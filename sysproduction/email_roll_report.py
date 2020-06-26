## Email roll data report
## We also have a report function to email

from sysproduction.diagnostic.reporting import run_report
from sysproduction.diagnostic.report_configs import roll_report_config

def email_roll_report():
    """

    Print information about whether futures contracts should be rolled

    :param instrument_code: The instrument code, for example 'AUD', 'CRUDE_W'. Specify ALL for everything
    :return: None, but print results
    """

    email_roll_report_config = roll_report_config.new_config_with_modified_output("email")
    email_roll_report_config.kwargs = dict(instrument_code = "ALL")
    run_report(roll_report_config)
