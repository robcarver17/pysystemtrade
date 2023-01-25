from syscore.constants import arg_not_supplied

from sysdata.data_blob import dataBlob
from sysproduction.reporting.api import reportingApi


def trades_report(
    data=arg_not_supplied,
    calendar_days_back=1,
    end_date=arg_not_supplied,
    start_date=arg_not_supplied,
):
    """
    Report on system status

    :param: data blob
    :return: list of formatted output items
    """
    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(
        data,
        start_date=start_date,
        end_date=end_date,
        calendar_days_back=calendar_days_back,
    )

    formatted_output = []
    formatted_output.append(reporting_api.std_header("Trades report"))
    list_of_table_names = [
        "table_of_orders_overview",
        "table_of_order_delays",
        "table_of_raw_slippage",
        "table_of_vol_slippage",
        "table_of_cash_slippage",
    ]

    for table_name in list_of_table_names:
        func = getattr(reporting_api, table_name)
        formatted_output.append(func())

    ## special case
    list_of_summary = reporting_api.list_of_cash_summary_text()
    formatted_output = formatted_output + list_of_summary

    formatted_output.append(reporting_api.footer())

    return formatted_output


if __name__ == "__main__":
    trades_report()
