from sysdata.data_blob import dataBlob

from syscore.objects import header, table, arg_not_supplied, body_text
from sysproduction.reporting.api import reportingApi


HEADER_TEXT = body_text("The following report calculates the minimum capital for a single contract as follows:\n" +
                        'A- point_size_base: Futures multiplier in base (account currency) = multiplier * fx rate \n' +
                        'B- price: Price\n' +
                        'C- annual_perc_stdev: Annual standard deviation in percentage terms (100 = 100%%)\n' +
                        'D- risk_target: Risk target in percentage terms (20 = 20%%)\n' +
                        'E- minimum_capital_one_contract:  Minimum capital to hold a single contract on a standalone basis = A * B * C / D \n' +
                        'F- minimum_position_contracts: Minimum position we want to hold for an average sized forecast\n' +
                        'G- instrument_weight: Proportion of capital allocated to instrument \n' +
                        'H- IDM: Instrument diversification multiplier \n' +
                        'I- minimum_capital: Minimum capital within a portfolio, allowing for minimum position = E * F / ( G * H) \n'
                        )

def minimum_capital_report(
    data: dataBlob = arg_not_supplied,


):

    if data is arg_not_supplied:
        data = dataBlob()

    reporting_api = reportingApi(
        data
    )

    formatted_output = []
    formatted_output.append(reporting_api.terse_header("Minimum capital report"))
    formatted_output.append(HEADER_TEXT)

    formatted_output.append(reporting_api.table_of_minimum_capital())

    formatted_output.append(reporting_api.footer())

    return formatted_output


if __name__ == '__main__':
    minimum_capital_report()
