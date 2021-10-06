import datetime

import pandas as pd

from syscore.objects import header, table, body_text
from sysproduction.utilities.risk_metrics import \
    get_correlation_matrix_all_instruments, \
    get_instruments_with_positions_all_strategies, get_risk_data_for_instrument, \
    get_portfolio_risk_for_all_strategies, get_portfolio_risk_across_strategies, sorted_clean_df


# FIX ME A VERY INEFFICIENT REPORT THAT COULD REALLY DO WITH SOME CACHING...
# BUT THEN MAYBE CACHING SHOULD BE INTRODUCED MORE GENERALLY AT SYSPRODUCTION_DATA LEVEL?
# ALSO, WHY DO WE GET POSITIONS FOR WHICH THE CURRENT POSITION IS ZERO?

def risk_report(data):
    """
    Get risk report info
    """
    results_dict = calculate_risk_report_data(data)
    formatted_output = format_risk_report(results_dict)

    return formatted_output


def calculate_risk_report_data(data):
    ## Correlations, instrument risk calcs, risk per instrument, portfolio risk total, portfolio risk for strategies
    corr_data = get_correlation_matrix_all_instruments(data)
    instrument_risk_data = get_instrument_risk_table(data)
    strategy_risk = get_portfolio_risk_across_strategies(data)
    portfolio_risk_total = get_portfolio_risk_for_all_strategies(data)

    result_dict = dict(corr_data = corr_data, instrument_risk_data = instrument_risk_data,
                  portfolio_risk_total = portfolio_risk_total, strategy_risk = strategy_risk)

    return result_dict

def format_risk_report(results_dict):
    """
    Put the results into a printable format

    :param results_dict: dict of risk tables
    :return:
    """


    formatted_output = []

    formatted_output.append(
        header(
            "Risk report produced on %s" % str(
                datetime.datetime.now())))

    result1 = results_dict['portfolio_risk_total']*100
    result1_text = body_text("Total risk across all strategies, annualised percentage %.1f" % result1)
    formatted_output.append(result1_text)

    table2_df = results_dict['strategy_risk']*100
    table2_df = table2_df.round(1)
    table2 = table("Risk per strategy, annualised percentage", table2_df)
    formatted_output.append(table2)

    table3_df = results_dict['instrument_risk_data']
    table3_df = table3_df.round(1)
    table3 = table("Instrument risk", table3_df)
    formatted_output.append(table3)

    table4_df = results_dict['corr_data'].as_pd()
    table4_df = table4_df.round(2)
    table4 = table("Correlations", table4_df)
    formatted_output.append(table4)

    formatted_output.append(header("END OF RISK REPORT"))

    return formatted_output


def get_instrument_risk_table(data):
    ## INSTRUMENT RISK (daily %, annual %, return space daily and annual, base currency per contract daily and annual, positions)
    instrument_list = get_instruments_with_positions_all_strategies(data)
    risk_data_list = dict([(instrument_code, get_risk_data_for_instrument(data, instrument_code))
                           for instrument_code in instrument_list])
    risk_df = pd.DataFrame(risk_data_list)
    risk_df = sorted_clean_df(risk_df, 'annual_risk_perc_capital')

    return risk_df


