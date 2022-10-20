from sysdata.data_blob import dataBlob

from syscore.objects import header, table, arg_not_supplied, body_text
from sysproduction.reporting.api import reportingApi

COSTS_REPORT_TEXT = body_text(
    "Cost calculations: Costs shown are expected costs per trade in Sharpe Ratio (SR) units and are calculated as follows: percentage_cost /  avg_annual_vol_perc "
)

def costs_report(
    data: dataBlob = arg_not_supplied,
        calendar_days_back = 250


):

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(
        data,
        calendar_days_back=calendar_days_back
    )

    formatted_output = []

    formatted_output.append(reporting_api.std_header("Costs report"))
    formatted_output.append(COSTS_REPORT_TEXT)

    formatted_output.append(header("Costs *including* BOTH spreads and commissions"))
    formatted_output.append(reporting_api.table_of_sr_costs())
    formatted_output.append(body_text("* indicates currently held position"))

    formatted_output.append(header("Costs *excluding* spreads, COMMISSION ONLY"))
    formatted_output.append(reporting_api.table_of_sr_costs(include_spreads=False))
    formatted_output.append(body_text("* indicates currently held position"))

    formatted_output.append(header("Costs *excluding* commissions, SPREADS ONLY"))
    formatted_output.append(reporting_api.table_of_sr_costs(include_commission=False))
    formatted_output.append(body_text("* indicates currently held position"))

    formatted_output.append(reporting_api.footer())

    return formatted_output

if __name__ == '__main__':
    costs_report()
