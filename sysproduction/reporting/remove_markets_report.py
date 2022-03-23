from sysdata.data_blob import dataBlob

from syscore.objects import header, table, arg_not_supplied, body_text
from sysproduction.reporting.api import reportingApi

HEADER_TEXT = body_text("report code not ready")

def remove_markets_report(
    data: dataBlob = arg_not_supplied,


):

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(
        data
    )

    formatted_output = []

    formatted_output.append(HEADER_TEXT)

    return formatted_output
