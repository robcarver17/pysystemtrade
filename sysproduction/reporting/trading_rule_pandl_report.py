## Plots account curves

import datetime
import datetime

from syscore.objects import header, table, body_text, arg_not_supplied

from sysdata.data_blob import dataBlob

from sysproduction.reporting.api import reportingApi

list_of_periods = ['YTD', '1Y', '3Y', '5Y', '10Y','20Y','99Y']


def trading_rule_pandl_report(data: dataBlob = arg_not_supplied,
                          start_date = arg_not_supplied,
                          end_date = arg_not_supplied):


    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(data, start_date=start_date, end_date=end_date)

    if (start_date is arg_not_supplied) and (end_date is arg_not_supplied):
        formatted_output = _trading_rule_report_full(reporting_api)
    else:
        formatted_output = _trading_rule_report_with_dates(reporting_api)


    return formatted_output

def _trading_rule_report_with_dates(
        reporting_api: reportingApi
) -> list:

    list_of_figures = reporting_api.trading_rule_figures_using_dates()

    return list_of_figures


def _trading_rule_report_full(
                                reporting_api: reportingApi) -> list:

    formatted_output = []

    for period in list_of_periods:
        try:
            list_of_figures = reporting_api.trading_rule_figures_given_period(period)
            formatted_output =+ list_of_figures
        except:
            print("Couldn't do a figure (weird time period %s?)" % period)

    return formatted_output
