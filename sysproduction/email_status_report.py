## Email roll data report
## We also have a report function to email

from sysproduction.diagnostic.reporting import run_report
from sysproduction.diagnostic.report_configs import status_report_config

def email_status_report():
    """

    Print and email information about current system status

    :return: None, but print results
    """

    config = status_report_config.new_config_with_modified_output("email")
    run_report(config)

