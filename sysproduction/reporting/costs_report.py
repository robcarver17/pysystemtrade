## Generate expected spread from actual trades, and sampled spreads
import datetime
from sysdata.data_blob import dataBlob

from syscore.objects import header, table, arg_not_supplied, body_text
from sysproduction.reporting.api import reportingApi

COSTS_REPORT_TEXT = body_text(
    "Cost calculations: Costs shown are in SR units and are calculated as follows:"
)

def costs_report(
    data: dataBlob = arg_not_supplied,
    calendar_days_back: int = 250,
    end_date: datetime.datetime = arg_not_supplied,
    start_date: datetime.datetime = arg_not_supplied,
):

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(
        data,
        start_date=start_date,
        end_date=end_date,
        calendar_days_back=calendar_days_back,
    )

    formatted_output = []

    formatted_output.append(reporting_api.std_header("Costs report"))
    formatted_output.append(COSTS_REPORT_TEXT)
    formatted_output.append(reporting_api.table_of_sr_costs())
    formatted_output.append(body_text("* indicates currently held position"))
    formatted_output.append(reporting_api.footer())

    return formatted_output
