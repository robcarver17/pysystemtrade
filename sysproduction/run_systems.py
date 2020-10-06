"""
Run overnight backtest of systems to generate optimal positions

These are defined in either the defaults.yaml file or overriden in private config
strategy_list:
  example:
    overnight_launcher:
      function: sysproduction.example_run_system.run_system
      backtest_config_filename: "systems.provided.futures_chapter15.futures_config.yaml",
      account_currency: "GBP"

"""
from syscore.objects import resolve_function

from sysproduction.data.get_data import dataBlob
from sysproduction.data.controls import diagProcessConfig
from sysproduction.run_process import processToRun
from sysproduction.data.strategies import get_list_of_strategies


def run_systems():
    process_name = "run_systems"
    data = dataBlob(log_name=process_name)
    list_of_timer_names_and_functions = get_list_of_timer_functions_for_strategies(
        process_name, data)
    system_process = processToRun(
        process_name,
        data,
        list_of_timer_names_and_functions,
        use_strategy_config=True)
    system_process.main_loop()


def get_list_of_timer_functions_for_strategies(process_name, data):
    list_of_strategy_names = get_list_of_strategies()
    list_of_timer_names_and_functions = []
    for strategy_name in list_of_strategy_names:
        object, method = get_strategy_object_and_method(
            process_name, data, strategy_name
        )
        strategy_tuple = (strategy_name, object, method)
        list_of_timer_names_and_functions.append(strategy_tuple)

    return list_of_timer_names_and_functions


def get_strategy_object_and_method(process_name, data, strategy_name):
    config_this_process = get_strategy_class_object_config(
        process_name, data, strategy_name
    )
    strategy_class_object = resolve_function(config_this_process.pop("object"))
    function = config_this_process.pop("function")

    # following are used by run process but not by us
    _ = config_this_process.pop("max_executions", None)
    _ = config_this_process.pop("frequency", None)

    other_args = config_this_process

    strategy_data = dataBlob(log_name=process_name)
    strategy_data.log.label(strategy_name=strategy_name)

    strategy_class_instance = strategy_class_object(
        strategy_data, strategy_name, **other_args
    )
    method = getattr(strategy_class_instance, function)

    return strategy_class_instance, method


def get_strategy_class_object_config(process_name, data, strategy_name):
    diag_config = diagProcessConfig(data)
    config_this_process = diag_config.get_strategy_dict_for_process(
        process_name, strategy_name
    )
    return config_this_process
