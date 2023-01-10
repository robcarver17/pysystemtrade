"""
Run overnight backtest of systems to generate optimal positions

"""

from sysdata.data_blob import dataBlob

from syscontrol.run_process import processToRun

from sysproduction.update_system_backtests import process_name, backtest_function
from syscontrol.strategy_tools import strategyRunner
from sysproduction.data.control_process import get_list_of_strategies_for_process


def run_systems():
    data = dataBlob(log_name=process_name)
    list_of_timer_names_and_functions = (
        get_list_of_backtest_timer_functions_for_strategies(data)
    )

    system_process = processToRun(process_name, data, list_of_timer_names_and_functions)
    system_process.run_process()


def backtest_function_to_be_renamed(self):
    self.run_strategy_method()


def get_list_of_backtest_timer_functions_for_strategies(data):
    list_of_strategy_names = get_list_of_strategies_for_process(data, process_name)
    list_of_timer_names_and_functions = []
    for strategy_name in list_of_strategy_names:
        # we add a method to the class with the strategy name, that just calls run_strategy_backtest with the current
        #    strategy
        setattr(strategyRunner, strategy_name, backtest_function_to_be_renamed)
        object = strategyRunner(data, strategy_name, process_name, backtest_function)

        strategy_tuple = (strategy_name, object)
        list_of_timer_names_and_functions.append(strategy_tuple)

    return list_of_timer_names_and_functions


if __name__ == "__main__":
    run_systems()
