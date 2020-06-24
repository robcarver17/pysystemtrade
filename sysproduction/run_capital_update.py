
from sysproduction.run_process import processToRun
from sysproduction.update_total_capital import totalCapitalUpdate
from sysproduction.update_strategy_capital import updateStrategyCapital
from sysproduction.data.get_data import dataBlob

def run_capital_update():
    process_name = "run_capital_update"
    data = dataBlob(log_name=process_name)
    list_of_timer_names_and_functions = get_list_of_timer_functions_for_capital_update(data)
    capital_process = processToRun(process_name, data, list_of_timer_names_and_functions)
    capital_process.main_loop()

def get_list_of_timer_functions_for_capital_update(data):
    total_capital_update_object = totalCapitalUpdate(data)
    strategy_capital_update_object = updateStrategyCapital(data)
    list_of_timer_names_and_functions = [
                        ('total_capital', total_capital_update_object.update_total_capital),
                        ('strategy_capital', strategy_capital_update_object.strategy_allocation)
                        ]

    return list_of_timer_names_and_functions

