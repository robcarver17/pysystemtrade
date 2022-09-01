"""
Ad-hoc trading rule report

Ad-hoc reports do not fit into the normal report framework and may include much hard coded ugliness
"""

# include these lines if running line by line in IDE console mode, but don't work in a headless server
#import matplotlib
#matplotlib.use("TkAgg")

import datetime
import pandas as pd
from sysproduction.data.backtest import dataBacktest
from syscore.dateutils import calculate_start_and_end_dates
from sysdata.data_blob import dataBlob
from sysproduction.reporting.formatting import make_account_curve_plot_from_df
from sysproduction.reporting.reporting_functions import parse_report_results, output_file_report, PdfOutputWithTempFileName
from sysproduction.reporting.report_configs import reportConfig

def trading_rule_pandl_adhoc_report(dict_of_rule_groups: dict,
                                    source_strategy: str,
                                    ):

    data = dataBlob()

    report_config = reportConfig(
        title="Trading rule p&l",
        function="not_used",
        output="file"
    )

    list_of_periods = ['YTD', '12M', '3Y', '5Y', '10Y','99Y']
    list_of_rule_groups = list(dict_of_rule_groups.keys())

    report_output = []

    for period in list_of_periods:
        try:
            start_date, end_date = calculate_start_and_end_dates(start_period=period)
            assert end_date>start_date
        except:
            continue

        for rule_group in list_of_rule_groups:
            ## We reload to avoid memory blowing up
            figure_object = get_figure_for_rule_group(rule_group=rule_group,
                dict_of_rule_groups=dict_of_rule_groups,
                data=data,
                source_strategy=source_strategy,
                                                      start_date=start_date,
                                                      end_date=end_date)

            report_output.append(figure_object)

    parsed_report_results = parse_report_results(data,
                                          report_results=report_output)

    output_file_report(parsed_report=parsed_report_results,
                       data=data, report_config=report_config)

def get_figure_for_rule_group(rule_group: str,
      data: dataBlob,
      source_strategy: str,
      dict_of_rule_groups: dict,
      start_date: datetime.datetime,
      end_date: datetime.datetime):

    data_backtest = dataBacktest()

    backtest = data_backtest.get_most_recent_backtest(source_strategy)
    rules = dict_of_rule_groups[rule_group]
    pandl_by_rule = dict([
        (rule_name, backtest.system.accounts.pandl_for_trading_rule(rule_name).percent.as_ts)
        for rule_name in rules
    ])
    concat_pd_by_rule = pd.concat(pandl_by_rule, axis=1)
    concat_pd_by_rule.columns = rules

    pdf_output = PdfOutputWithTempFileName(data)
    make_account_curve_plot_from_df(concat_pd_by_rule,
                                    start_of_title="Total p&l",
                                    start_date=start_date,
                                    end_date=end_date)

    figure_object = pdf_output.save_chart_close_and_return_figure()

    return figure_object

if __name__ == '__main__':
    dict_of_rule_groups = dict(
        acceleration = ['accel16', 'accel32', 'accel64'],
                       asset_class_trend = ['assettrend16', 'assettrend2', 'assettrend32', 'assettrend4', 'assettrend64', 'assettrend8'],
                        breakout = ['breakout10', 'breakout160', 'breakout20', 'breakout320', 'breakout40', 'breakout80'],
                        ewmac_momentum =  ['momentum16', 'momentum32', 'momentum4', 'momentum64', 'momentum8'],
                        normalised_momentum = ['normmom16', 'normmom2', 'normmom32', 'normmom4', 'normmom64', 'normmom8'],
                       relative_momentum = ['relmomentum10', 'relmomentum20', 'relmomentum40', 'relmomentum80'],
                       carry=['carry10', 'carry125', 'carry30', 'carry60'],
                        relative_carry = ['relcarry'],

                     skew = ['skewabs180', 'skewabs365', 'skewrv180', 'skewrv365'],
                        misc_mr = ['mrinasset160', 'mrwrings4'])

    source_strategy = 'dynamic_TF_carry'
    trading_rule_pandl_adhoc_report(source_strategy=source_strategy,
                                    dict_of_rule_groups=dict_of_rule_groups)
