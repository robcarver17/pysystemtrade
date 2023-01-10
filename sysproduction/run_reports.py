from syscontrol.run_process import processToRun

from sysdata.data_blob import dataBlob

from sysproduction.data.reports import dataReports

# JUST A COPY AND PASTE JOB RIGHT NOW


def run_reports():
    process_name = "run_reports"
    data = dataBlob(log_name=process_name)
    list_of_timer_names_and_functions = get_list_of_timer_functions_for_reports(data)
    report_process = processToRun(process_name, data, list_of_timer_names_and_functions)
    report_process.run_process()


def get_list_of_timer_functions_for_reports(data):
    list_of_timer_names_and_functions = []
    data_reports = dataReports(data)
    all_configs = data_reports.get_report_configs_to_run()

    for report_name, report_config in all_configs.items():
        data_for_report = dataBlob(log_name=report_name)
        report_object = runReport(data_for_report, report_config, report_name)
        report_tuple = (report_name, report_object)
        list_of_timer_names_and_functions.append(report_tuple)

    return list_of_timer_names_and_functions


from sysproduction.reporting.reporting_functions import run_report


class runReport(object):
    def __init__(self, data, config, report_function):
        self.data = data
        self.config = config

        # run process expects a method with same name as log name
        setattr(self, report_function, self.run_generic_report)

    def run_generic_report(self):
        ## Will be renamed
        run_report(self.config, data=self.data)


if __name__ == "__main__":
    run_reports()
