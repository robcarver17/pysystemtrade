"""
Ad-hoc trading rule report

Ad-hoc reports do not fit into the normal report framework and may include much hard coded ugliness
"""

# include these lines if running line by line in IDE console mode, but don't work in a headless server
# import matplotlib
# matplotlib.use("TkAgg")

import datetime
import pandas as pd
from sysproduction.data.backtest import dataBacktest
from syscore.dateutils import get_date_from_period_and_end_date
from sysdata.data_blob import dataBlob
from sysproduction.reporting.formatting import make_account_curve_plot_from_df
from sysproduction.reporting.reporting_functions import (
    parse_report_results,
    output_file_report,
    PdfOutputWithTempFileName,
)
from sysproduction.reporting.report_configs import reportConfig

from systems.provided.rob_system.run_system import futures_system, System


def trading_rule_pandl_adhoc_report(
    dict_of_rule_groups: dict,
    system_function,
):

    data = dataBlob()
    report_config = reportConfig(
        title="Trading rule p&l", function="not_used", output="file"
    )

    list_of_periods = ["YTD", "1Y", "3Y", "10Y", "99Y"]
    list_of_rule_groups = list(dict_of_rule_groups.keys())

    report_output = []

    for rule_group in list_of_rule_groups:
        ## We reload to avoid memory blowing up

        system = system_function()
        system.get_instrument_list(
            remove_duplicates=True,
            remove_ignored=True,
            remove_trading_restrictions=True,
            remove_bad_markets=True,
        )

        for period in list_of_periods:
            start_date = get_date_from_period_and_end_date(period)

            figure_object = get_figure_for_rule_group(
                rule_group=rule_group,
                dict_of_rule_groups=dict_of_rule_groups,
                data=data,
                system=system,
                start_date=start_date,
                period_label=period,
            )

            report_output.append(figure_object)

    parsed_report_results = parse_report_results(data, report_results=report_output)

    output_file_report(
        parsed_report=parsed_report_results, data=data, report_config=report_config
    )


def get_figure_for_rule_group(
    rule_group: str,
    data: dataBlob,
    system: System,
    dict_of_rule_groups: dict,
    start_date: datetime.datetime,
    period_label: str,
):

    rules = dict_of_rule_groups[rule_group]
    pandl_by_rule = dict(
        [
            (rule_name, system.accounts.pandl_for_trading_rule(rule_name).percent.as_ts)
            for rule_name in rules
        ]
    )
    concat_pd_by_rule = pd.concat(pandl_by_rule, axis=1)
    concat_pd_by_rule.columns = rules

    pdf_output = PdfOutputWithTempFileName(data)
    make_account_curve_plot_from_df(
        concat_pd_by_rule,
        start_of_title=f"Total Trading Rule P&L for period '{period_label}'",
        start_date=start_date,
        title_style={"size": 6},
    )

    figure_object = pdf_output.save_chart_close_and_return_figure()

    return figure_object


if __name__ == "__main__":
    dict_of_rule_groups = dict(
        acceleration=["accel16", "accel32", "accel64"],
        asset_class_trend=[
            "assettrend16",
            "assettrend2",
            "assettrend32",
            "assettrend4",
            "assettrend64",
            "assettrend8",
        ],
        breakout=[
            "breakout10",
            "breakout160",
            "breakout20",
            "breakout320",
            "breakout40",
            "breakout80",
        ],
        ewmac_momentum=[
            "momentum16",
            "momentum32",
            "momentum4",
            "momentum64",
            "momentum8",
        ],
        normalised_momentum=[
            "normmom16",
            "normmom2",
            "normmom32",
            "normmom4",
            "normmom64",
            "normmom8",
        ],
        relative_momentum=[
            "relmomentum10",
            "relmomentum20",
            "relmomentum40",
            "relmomentum80",
        ],
        carry=["carry10", "carry125", "carry30", "carry60"],
        relative_carry=["relcarry"],
        skew=["skewabs180", "skewabs365", "skewrv180", "skewrv365"],
        misc_mr=["mrinasset160", "mrwrings4"],
    )

    trading_rule_pandl_adhoc_report(
        system_function=futures_system, dict_of_rule_groups=dict_of_rule_groups
    )
