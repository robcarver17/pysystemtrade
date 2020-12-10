from syscontrol.strategy_tools import strategyRunner


from sysdata.data_blob import dataBlob
from sysproduction.data.control_process import get_list_of_strategies_for_process

backtest_function = "run_backtest"
process_name = "run_systems"


def update_system_backtests():
    ## function if called from script
    with dataBlob(log_name="Update-System_Backtest") as data:
        list_of_strategies = get_list_of_strategies_for_process(data, process_name)
        for strategy_name in list_of_strategies:
            system_backtest_runner = strategyRunner(data, strategy_name, process_name, backtest_function)
            system_backtest_runner.run_strategy_method()


