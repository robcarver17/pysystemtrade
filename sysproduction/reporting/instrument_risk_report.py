from sysdata.data_blob import dataBlob

from syscore.objects import header, table, arg_not_supplied, body_text
from sysproduction.reporting.api import reportingApi

HEADER_TEXT = body_text("Risk calculation for different instruments, columns as follows:\n"+
                        "A- daily_price_stdev: Standard deviation, price points, per day\n"+
                        "B- annual_price_stdev: Standard deviation, price points, per year =A*16       \n"+
                        "C- price: Price  \n"+
                        "D- daily_perc_stdev: Standard deviation, percentage (1=1%%), per day =A*C \n"+
                        "E- annual_perc_stdev: Standard deviation, percentage (1=1%%), per year = B*C = D*16  \n"+
                        "F- point_size_base: Futures multiplier in base (account) currency  \n"+
                        "G- contract_exposure: Notional value of one contract = F*C  \n"+
                        "H- annual_risk_per_contract: Standard deviation, base currency, per year = B * F = E * G")

def instrument_risk_report(
    data: dataBlob = arg_not_supplied,


):

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(
        data
    )

    formatted_output = []
    formatted_output.append(
        reporting_api.terse_header("Instrument risk report"))
    formatted_output.append(HEADER_TEXT)
    formatted_output.append("Sort by annual percentage standard deviation")
    formatted_output.append(reporting_api.table_of_risk_all_instruments(sort_by='annual_perc_stdev'))
    formatted_output.append("Sort by annual currency risk per contract")
    formatted_output.append(reporting_api.table_of_risk_all_instruments(sort_by='annual_risk_per_contract'))
    formatted_output.append("Sort by notional value base currency")
    formatted_output.append(reporting_api.table_of_risk_all_instruments(sort_by='contract_exposure'))

    formatted_output.append(reporting_api.footer())


    return formatted_output
