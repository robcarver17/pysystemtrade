from copy import copy

from syscore.constants import missing_data

from sysproduction.data.generic_production_data import productionDataLayerGeneric

from sysproduction.reporting.report_configs import report_config_defaults, reportConfig


class dataReports(productionDataLayerGeneric):
    def get_report_configs_to_run(self) -> dict:
        ## return dictionary of all report configs to run
        config_dict_from_yaml = self.get_reporting_config_dict()
        default_config = self.get_default_reporting_config_dict()

        report_config = populate_reporting_config_from_yaml_input(
            config_dict_from_yaml=config_dict_from_yaml, default_config=default_config
        )

        return report_config

    def get_reporting_config_dict(self) -> dict:
        config = self.data.config
        report_config_dict = config.get_element_or_missing_data("reports")
        if report_config_dict is missing_data:
            return {}
        else:
            return report_config_dict

    def get_default_reporting_config_dict(self) -> dict:
        return report_config_defaults


def populate_reporting_config_from_yaml_input(
    config_dict_from_yaml: dict, default_config: dict
) -> dict:

    if len(config_dict_from_yaml) == 0:
        return default_config

    reports_to_run = config_dict_from_yaml.keys()
    new_config = dict(
        [
            (
                report_name,
                _resolve_config_for_named_report(
                    report_name=report_name,
                    config_dict_from_yaml=config_dict_from_yaml,
                    default_config=default_config,
                ),
            )
            for report_name in reports_to_run
        ]
    )

    return new_config


def _resolve_config_for_named_report(
    report_name: str, config_dict_from_yaml: dict, default_config: dict
) -> reportConfig:

    default_config_for_report = default_config[report_name]
    new_config_for_report = config_dict_from_yaml[report_name]

    if type(new_config_for_report) is str:
        ### no config, just report name
        return default_config_for_report

    resolved_config = _resolve_config_from_config_pair(
        default_config_for_report, new_config_for_report=new_config_for_report
    )

    return resolved_config


def _resolve_config_from_config_pair(
    default_config_for_report: reportConfig, new_config_for_report: dict
) -> reportConfig:

    new_config = copy(default_config_for_report)
    attr_names = new_config_for_report.keys()
    for attribute in attr_names:
        setattr(new_config, attribute, new_config_for_report[attribute])

    return new_config
