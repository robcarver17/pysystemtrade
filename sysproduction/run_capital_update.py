from syscontrol.run_process import processToRun
from sysproduction.update_total_capital import totalCapitalUpdate
from sysproduction.update_strategy_capital import updateStrategyCapital
from sysdata.data_blob import dataBlob


def run_capital_update():
    process_name = "run_capital_update"
    data = dataBlob(log_name=process_name)
    list_of_timer_names_and_functions = get_list_of_timer_functions_for_capital_update()
    capital_process = processToRun(
        process_name, data, list_of_timer_names_and_functions
    )
    capital_process.run_process()


def get_list_of_timer_functions_for_capital_update():
    data_total_capital = dataBlob(log_name="update_total_capital")
    data_strategy_capital = dataBlob(log_name="strategy_allocation")

    total_capital_update_object = totalCapitalUpdate(data_total_capital)
    strategy_capital_update_object = updateStrategyCapital(data_strategy_capital)
    list_of_timer_names_and_functions = [
        ("update_total_capital", total_capital_update_object),
        ("strategy_allocation", strategy_capital_update_object),
    ]

    return list_of_timer_names_and_functions


if __name__ == "__main__":
    run_capital_update()
