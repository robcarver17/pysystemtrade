from syscore.constants import arg_not_supplied
from sysdata.data_blob import dataBlob

from sysproduction.reporting.api import reportingApi

# We want a p&l (We could merge this into another kind of report)
# We want to be able to have it emailed, or run it offline
# To have it emailed, we'll call the report function and optionally pass the output to a text file not stdout
# Reports consist of multiple calls to functions with data object, each of which returns a displayable object
# We also chuck in a title and a timestamp


def pandl_report(
    data: dataBlob = arg_not_supplied,
    calendar_days_back=7,
    start_date=arg_not_supplied,
    end_date=arg_not_supplied,
):
    """

    To begin with we calculate::

    - change in total p&l from total capital
    - p&l for each instrument, by summing over p&l per contract

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
    formatted_output.append(reporting_api.std_header("Profit and loss report"))
    list_of_func_names = [
        "body_text_total_capital_pandl",
        "table_pandl_for_instruments_across_strategies",
        "body_text_total_pandl_for_futures",
        "body_text_residual_pandl",
        "table_strategy_pandl_and_residual",
        "table_sector_pandl",
    ]

    for func_name in list_of_func_names:
        func = getattr(reporting_api, func_name)
        formatted_output.append(func())

    formatted_output.append(reporting_api.footer())

    return formatted_output


if __name__ == "__main__":
    pandl_report()
