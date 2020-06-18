## Email roll data report
## We also have a report function to email

from sysproduction.diagnostic.reporting import run_report
from syscore.objects import report_config


def email_daily_pandl_report():


    pandl_report_config = report_config(title="One day P&L report",
                                       function="sysproduction.diagnostic.profits.pandl_info",
                                       output="email")

    run_report(pandl_report_config, calendar_days_back = 1)
