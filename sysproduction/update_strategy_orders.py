from syscore.interactive.menus import print_menu_of_values_and_get_response
from syscontrol.strategy_tools import strategyRunner

from sysdata.data_blob import dataBlob
from sysproduction.data.control_process import get_list_of_strategies_for_process
from sysexecution.strategies.strategy_order_handling import (
    name_of_main_generator_method,
)

process_name = "run_strategy_order_generator"


def update_strategy_orders():
    ## function if called from script
    with dataBlob(log_name="Update-Strategy-Orders") as data:

        list_of_strategies = get_list_of_strategies_for_process(data, process_name)
        ALL = "ALL"
        print("Which strategy?")
        strategy_name = print_menu_of_values_and_get_response(
            list_of_strategies, default_str=ALL
        )

        if not strategy_name == ALL:
            list_of_strategies = [strategy_name]

        for strategy_name in list_of_strategies:
            strategy_order_generator = strategyRunner(
                data, strategy_name, process_name, name_of_main_generator_method
            )
            strategy_order_generator.run_strategy_method()
