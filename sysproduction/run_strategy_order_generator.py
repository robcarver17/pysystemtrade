"""
Generate orders for strategies

These are 'virtual' orders, not contract specific

This is a 'run' module, designed to run all day and then stop at the end of the day


"""

from sysdata.data_blob import dataBlob
from syscontrol.run_process import processToRun
from sysproduction.run_systems import get_list_of_timer_functions_for_strategies

process_name = "run_strategy_order_generator"


def run_strategy_order_generator():
    data = dataBlob(log_name=process_name)
    list_of_timer_names_and_functions = get_list_of_timer_functions_for_strategies(
        process_name, data)
    order_process = processToRun(
        process_name,
        data,
        list_of_timer_names_and_functions,
        use_strategy_config=True)
    order_process.main_loop()
