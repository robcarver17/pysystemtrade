
from sysproduction.diagnostic.reporting import run_report
from sysproduction.diagnostic.report_configs import trade_report_config

def email_trades_report():


    config = trade_report_config.new_config_with_modified_output("email")
    config.modify_kwargs(calendar_days_back = 1)
    run_report(config)
