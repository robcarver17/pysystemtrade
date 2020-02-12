## Console roll data report
## We also have a report function to email

from sysproduction.diagnostic.reporting import run_report
from syscore.objects import report_config


def get_roll_info(instrument_code: str = "ALL"):
    """

    Print information about whether futures contracts should be rolled

    :param instrument_code: The instrument code, for example 'AUD', 'CRUDE_W'. Specify ALL for everything
    :return: None, but print results
    """

    roll_report_config = report_config(title="Roll report",
                                       function="sysproduction.diagnostic.rolls.roll_info",
                                       output="console")

    run_report(roll_report_config, instrument_code = instrument_code)
