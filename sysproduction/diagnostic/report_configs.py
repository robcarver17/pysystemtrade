from copy import copy

class reportConfig(object):
    def __init__(self, title, function, output="console", **kwargs):
        assert output in ['console', 'email']
        self.title = title
        self.function = function
        self.output = output
        self.kwargs = kwargs

    def new_config_with_modified_output(self, output):
        new_config = copy(self)
        new_config.output = output

        return new_config

    def new_config_with_modify_kwargs(self, **kwargs):
        new_config = copy(self)
        for key in kwargs.keys():
            new_config.kwargs[key] = kwargs[key]

        return new_config


status_report_config = reportConfig(title="Status report",
                                   function="sysproduction.diagnostic.system_status.system_status")


roll_report_config = reportConfig(title="Roll report",
                                   function="sysproduction.diagnostic.rolls.roll_info",
                                  instrument_code = "ALL")


daily_pandl_report_config = reportConfig(title="One day P&L report",
                                    function="sysproduction.diagnostic.profits.pandl_info", calendar_days_back = 1)


