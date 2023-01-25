## Generate list of instruments ranked by liquidity: # of contracts per day and

import datetime
import datetime

from syscore.constants import arg_not_supplied
from sysproduction.reporting.reporting_functions import table, header, body_text

from sysdata.data_blob import dataBlob

from sysproduction.reporting.api import reportingApi

list_of_periods = ["1B", "7D", "1M", "3M", "6M", "YTD", "12M"]
MARKET_REPORT = body_text(
    "This report lists instruments by their percentage returns, over different periods (eg 1 day, 7 days, 1 month, 3 months, 6 months, YTD and 1 year) \n"
    + "The first few tables are top6/bottom 6, then subsequently we have all instruments.\n"
    + "The return tables are sorted by instrument name, outright percentage return (1=1%), and vol adjusted return.\n"
    + "Search by period/order eg 1B/name, 1M/change, YTD/vol_adjusted \n+"
    "Periods: %s" % list_of_periods
)

MARKET_REPORT_CUSTOM_DATES = body_text(
    "This report lists instruments by their percentage returns, over different periods\n"
    + "The return tables are sorted by instrument name, outright percentage return (1=1%), and vol adjusted return"
)


def market_monitor_report(
    data: dataBlob = arg_not_supplied,
    start_date=arg_not_supplied,
    end_date=arg_not_supplied,
):

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(data, start_date=start_date, end_date=end_date)

    if (start_date is arg_not_supplied) and (end_date is arg_not_supplied):
        formatted_output = _market_monitor_report_full(reporting_api)
    else:
        formatted_output = _market_monitor_with_dates(reporting_api)

    formatted_output.append(reporting_api.footer())

    return formatted_output


def _market_monitor_with_dates(reporting_api: reportingApi) -> list:
    formatted_output = []
    formatted_output.append(reporting_api.std_header("Market monitor report"))
    formatted_output.append(MARKET_REPORT_CUSTOM_DATES)

    # eg 1 day, 7 days, 1 month, 3 months, 6 months, YTD and 1 year
    truncate = True
    for sortby in ["change", "vol_adjusted"]:
        formatted_output.append(
            reporting_api.table_of_market_moves_using_dates(
                sortby=sortby, truncate=truncate
            )
        )

    truncate = False
    for sortby in ["name", "change", "vol_adjusted"]:
        formatted_output.append(
            reporting_api.table_of_market_moves_using_dates(
                sortby=sortby, truncate=truncate
            )
        )

    return formatted_output


def _market_monitor_report_full(reporting_api: reportingApi) -> list:

    formatted_output = []
    formatted_output.append(reporting_api.terse_header("Market monitor report"))
    formatted_output.append(MARKET_REPORT)

    # eg 1 day, 7 days, 1 month, 3 months, 6 months, YTD and 1 year
    truncate = True
    for period in list_of_periods:
        for sortby in ["change", "vol_adjusted"]:
            formatted_output.append(
                reporting_api.table_of_market_moves_given_period(
                    period=period, sortby=sortby, truncate=truncate
                )
            )

    truncate = False
    for period in list_of_periods:
        for sortby in ["name", "change", "vol_adjusted"]:
            formatted_output.append(
                reporting_api.table_of_market_moves_given_period(
                    period=period, sortby=sortby, truncate=truncate
                )
            )

    return formatted_output


if __name__ == "__main__":
    market_monitor_report()
