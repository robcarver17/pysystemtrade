## Generate list of instruments ranked by liquidity: # of contracts per day and

import datetime

from syscore.constants import arg_not_supplied
from sysproduction.reporting.reporting_functions import table, header, body_text

from sysdata.data_blob import dataBlob

from sysproduction.reporting.api import reportingApi

LIQUIDITY_TEXT = body_text(
    "This report reports on the liquidity of various futures contracts. \n"
    + "The volumes in contracts are for the expiry which currently has the highest volume, and are averaged over the last four weeks\n"
    + "The risk shown is the volume translated into risk in $million. We multiply the contracts by the risk per contract, as an annual $ amount\n"
    + "It's recommended that the minimum volume a retail trader considers is 100 contracts or $1.5m per day"
    + "(*) indicates a position currently held in my own trading system"
)


def liquidity_report(data: dataBlob = arg_not_supplied):
    if data is arg_not_supplied:
        data = dataBlob()

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(data)
    formatted_output = []
    formatted_output.append(reporting_api.terse_header("Liquidity report"))
    formatted_output.append(LIQUIDITY_TEXT)
    formatted_output.append(reporting_api.table_of_liquidity_contract_sort())
    formatted_output.append(reporting_api.table_of_liquidity_risk_sort())
    formatted_output.append(reporting_api.footer())

    return formatted_output


if __name__ == "__main__":
    liquidity_report()
