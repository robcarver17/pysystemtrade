from sysdata.data_blob import dataBlob

from syscore.objects import header, table, arg_not_supplied, body_text
from sysproduction.reporting.api import reportingApi

HEADER_TEXT = body_text("List of markets which should be marked as untradeable due to risk, liquidity or cost issues")

def remove_markets_report(
    data: dataBlob = arg_not_supplied,


):

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(
        data
    )

    formatted_output = []

    formatted_output.append(reporting_api.terse_header("Removed markets report"))
    formatted_output.append(HEADER_TEXT)
    list_of_func_names = [
        "body_text_existing_markets_remove",
        "body_text_removed_markets_addback",
        "body_text_expensive_markets",
        "body_text_markets_without_enough_volume_risk",
        "body_text_markets_without_enough_volume_contracts"
        "body_text_too_safe_markets",

    ]

    for func_name in list_of_func_names:
        func = getattr(reporting_api, func_name)
        formatted_output.append(func())


    formatted_output.append(reporting_api.footer())

    return formatted_output
