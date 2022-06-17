## Generate list of instruments ranked by liquidity: # of contracts per day and

import datetime

from syscore.objects import header, table, body_text, arg_not_supplied

from sysdata.data_blob import dataBlob

from sysproduction.reporting.api import reportingApi

list_of_periods = ['1B', '7D', '1M', '3M', '6M', 'YTD', '12M']
MARKET_REPORT = body_text("This report lists instruments by their returns, over different periods (eg 1 day, 7 days, 1 month, 3 months, 6 months, YTD and 1 year) \n"+
                "The first few tables are top6/bottom 6, then subsequently we have all instruments.\n"+
                 "The return tables are sorted by instrument name, outright return, and vol adjusted return.\n" +
                 "Search by period/order eg 1B/name, 1M/change, YTD/vol_adjusted \n+"
                 "Periods: %s" % list_of_periods)

def market_monitor_report(data: dataBlob = arg_not_supplied):
    if data is arg_not_supplied:
        data = dataBlob()

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(data)
    formatted_output = []
    formatted_output.append(reporting_api.terse_header("Market monitor report"))
    formatted_output.append(MARKET_REPORT)
    #eg 1 day, 7 days, 1 month, 3 months, 6 months, YTD and 1 year
    truncate = True
    for period in list_of_periods:
        for sortby in [ 'change', 'vol_adjusted']:
            formatted_output.append(
                reporting_api.table_of_market_moves(
                    period=period, sortby=sortby, truncate=truncate))

    truncate = False
    for period in list_of_periods:
        for sortby in ['name', 'change', 'vol_adjusted']:
            formatted_output.append(
                reporting_api.table_of_market_moves(
                    period=period, sortby=sortby, truncate=truncate))

    formatted_output.append(reporting_api.footer())

    return formatted_output
