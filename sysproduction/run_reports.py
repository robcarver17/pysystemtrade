from sysproduction.run_process import processToRun
from sysproduction.diagnostic.report_configs import all_configs

from sysdata.data_blob import dataBlob


# JUST A COPY AND PAST JOB RIGHT NOW


def run_reports():
    process_name = "run_reports"
    data = dataBlob(log_name=process_name)
    list_of_timer_names_and_functions = get_list_of_timer_functions_for_reports()
    price_process = processToRun(
        process_name, data, list_of_timer_names_and_functions)
    price_process.main_loop()


def get_list_of_timer_functions_for_reports():
    list_of_timer_names_and_functions = []
    for report_name, report_config in all_configs.items():
        data_for_report = dataBlob(log_name=report_name)
        email_report_config = report_config.new_config_with_modified_output(
            "email")
        report_object = runReport(
            data_for_report,
            email_report_config,
            report_name)
        report_tuple = (report_name, report_object)
        list_of_timer_names_and_functions.append(report_tuple)

    return list_of_timer_names_and_functions


from sysproduction.diagnostic.reporting import run_report


class runReport(object):
    def __init__(self, data, config, report_function):
        self.data = data
        self.config = config

        # run process expects a method with same name as log name
        setattr(self, report_function, self.email_trades_report)

    def email_trades_report(self):

        run_report(self.config, data=self.data)
