# Functions to access strategy reports
"""
A strategy report is highly specific to a strategy, and will delve into the internals of the backtest state


"""

from syscore.objects import arg_not_supplied

from sysdata.data_blob import dataBlob
from sysproduction.data.backtest import dataBacktest
from sysproduction.data.strategies import get_list_of_strategies
from sysproduction.strategy_code.strategy_report import (
    get_reporting_function_instance_for_strategy_name,
)

ALL_STRATEGIES = "ALL"


def strategy_report(
    data=arg_not_supplied, timestamp=arg_not_supplied, strategy_name=ALL_STRATEGIES
):

    if data is arg_not_supplied:
        data = dataBlob()

    if strategy_name == ALL_STRATEGIES:
        list_of_strategies = get_list_of_strategies(data=data)
        if timestamp is not arg_not_supplied:
            # use print not logs as will only happen interactively
            print("Timestamp will be ignored as running ALL strategy reports")
            timestamp = arg_not_supplied
    else:
        list_of_strategies = [strategy_name]

    formatted_output = get_strategies_report_output(
        data, list_of_strategies, timestamp=timestamp
    )

    return formatted_output


def get_strategies_report_output(data, list_of_strategies, timestamp=arg_not_supplied):

    formatted_output = []
    for strategy_name in list_of_strategies:
        try:
            strategy_format_output_list = get_output_for_single_strategy(
                data, strategy_name, timestamp=timestamp
            )
            for output_item in strategy_format_output_list:
                formatted_output.append(output_item)
        except FileNotFoundError as e:
            print(e)

    return formatted_output


def get_output_for_single_strategy(data, strategy_name, timestamp=arg_not_supplied):
    strategy_reporting_function = get_reporting_function_instance_for_strategy_name(
        data, strategy_name
    )
    data_backtest = dataBacktest(data)
    if timestamp is arg_not_supplied:
        backtest = data_backtest.get_most_recent_backtest(strategy_name)
    else:
        backtest = data_backtest.load_backtest(strategy_name, timestamp)

    strategy_format_output_list = strategy_reporting_function(data, backtest)

    return strategy_format_output_list


if __name__ == "__main__":
    strategy_report()
