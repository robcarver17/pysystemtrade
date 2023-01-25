## Plots account curves

import datetime
import datetime

from syscore.constants import arg_not_supplied
from sysproduction.reporting.reporting_functions import table, header, body_text

from sysdata.data_blob import dataBlob

from sysproduction.reporting.api import reportingApi

list_of_periods = ["YTD", "12M", "3Y", "5Y", "10Y", "99Y"]


def account_curve_report(
    data: dataBlob = arg_not_supplied,
    start_date=arg_not_supplied,
    end_date=arg_not_supplied,
):

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(data, start_date=start_date, end_date=end_date)

    if (start_date is arg_not_supplied) and (end_date is arg_not_supplied):
        formatted_output = _account_curve_report_full(reporting_api)
    else:
        formatted_output = _account_curve_report_with_dates(reporting_api)

    return formatted_output


def _account_curve_report_with_dates(reporting_api: reportingApi) -> list:

    figure_object = reporting_api.figure_of_account_curve_using_dates()

    return [figure_object]


def _account_curve_report_full(reporting_api: reportingApi) -> list:

    formatted_output = []

    for period in list_of_periods:
        try:
            figure_object = reporting_api.figure_of_account_curves_given_period(period)
            formatted_output.append(figure_object)
        except:
            print("Couldn't do a figure (weird time period %s?)" % period)

    return formatted_output


if __name__ == "__main__":
    account_curve_report()
