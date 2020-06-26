## Email roll data report
## We also have a report function to email

from sysproduction.diagnostic.reporting import run_report
from sysproduction.diagnostic.report_configs import daily_pandl_report_config

def email_daily_pandl_report():


    config = daily_pandl_report_config.new_config_with_modified_output("email")
    config.kwargs = dict(calendar_days_back = 1)
    run_report(daily_pandl_report_config)
