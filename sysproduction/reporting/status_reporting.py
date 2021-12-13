"""
Monitor health of system by seeing when things last run

We can also check: when last adjusted prices were updated, when FX was last updated, when optimal position was
   last updated
"""


from syscore.objects import arg_not_supplied

from sysdata.data_blob import dataBlob

from sysproduction.reporting.api import reportingApi


def system_status(data: dataBlob = arg_not_supplied):
    """
    Report on system status

    :param: data blob
    :return: list of formatted output items
    """
    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(data)
    formatted_output = []
    formatted_output.append(reporting_api.terse_header("Status report"))
    list_of_func_names = [
        "table_of_control_config_list_for_all_processes",
        "table_of_control_status_list_for_all_processes",
        "table_of_process_status_list_for_all_processes",
        "table_of_control_data_list_for_all_methods",
        "table_of_last_price_updates",
        "table_of_last_optimal_position_updates",
        "table_of_trade_limits",
        "table_of_position_limits",
        "table_of_overrides",
        "body_text_of_position_locks",
    ]

    for func_name in list_of_func_names:
        func = getattr(reporting_api, func_name)
        formatted_output.append(func())

    formatted_output.append(reporting_api.footer())

    return formatted_output
