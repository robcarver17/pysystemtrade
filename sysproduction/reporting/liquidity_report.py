## Generate list of instruments ranked by liquidity: # of contracts per day and

import datetime

from syscore.objects import header, table, body_text, arg_not_supplied

from sysdata.data_blob import dataBlob

from sysproduction.reporting.api import reportingApi


def liquidity_report(data: dataBlob=arg_not_supplied):
    if data is arg_not_supplied:
        data = dataBlob()

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(data)
    formatted_output = []
    formatted_output.append(reporting_api.terse_header("Liquidity report"))
    formatted_output.append(reporting_api.table_of_liquidity_contract_sort())
    formatted_output.append(reporting_api.table_of_liquidity_risk_sort())
    formatted_output.append(reporting_api.footer())

    return formatted_output



