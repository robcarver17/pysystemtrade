
from sysproduction.diagnostic.reporting import run_report
from sysproduction.diagnostic.report_configs import reconcile_report_config

def email_reconcile_report():


    config = reconcile_report_config.new_config_with_modified_output("email")
    run_report(config)
