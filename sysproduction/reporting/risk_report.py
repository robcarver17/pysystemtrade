from syscore.constants import arg_not_supplied
from sysdata.data_blob import dataBlob
from sysproduction.reporting.api import reportingApi


def risk_report(data: dataBlob = arg_not_supplied):
    """
    Get risk report info
    """
    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(data)
    formatted_output = []
    formatted_output.append(reporting_api.terse_header("Risk report"))
    list_of_func_names = [
        "body_text_portfolio_risk_total",
        "body_text_margin_usage",
        "table_of_strategy_risk",
        "table_of_risk_by_asset_class",
        "table_of_beta_loadings_by_asset_class",
        "table_of_instrument_risk",
        "body_text_abs_total_all_risk_perc_capital",
        "body_text_abs_total_all_risk_annualised",
        "body_text_net_total_all_risk_annualised",
        "table_of_correlations",
    ]

    for func_name in list_of_func_names:
        func = getattr(reporting_api, func_name)
        formatted_output.append(func())

    formatted_output.append(reporting_api.footer())

    return formatted_output


if __name__ == "__main__":
    risk_report()
