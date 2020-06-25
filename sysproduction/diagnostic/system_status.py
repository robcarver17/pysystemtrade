"""
Monitor health of system by seeing when things last run

We can also check: when last adjusted prices were updated, when FX was last updated, when optimal position was
   last updated, when instrument orders were last submitted for a particular strategy,
   wether there are any outstanding broker orders

"""
from collections import  namedtuple

import pandas as pd

from syscore.objects import missing_data
from syscore.pdutils import make_df_from_list_of_named_tuple
from sysproduction.data.get_data import dataBlob
from sysproduction.data.controls import diagProcessConfig, dataControlProcess
from sysproduction.data.sim_data import get_list_of_strategies
from sysproduction.data.prices import get_list_of_instruments
from sysproduction.data.currency_data import get_list_of_fxcodes
from syslogdiag.log import accessLogFromMongodb



pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)




list_of_instruments = get_list_of_instruments()






dataForProcess = namedtuple("dataForProcess", ['name','running','start','end','status', 'finished_in_last_day',
                                               'start_time', 'end_time', 'required_machine', 'right_machine',
                                               'time_to_run', 'previous_required', 'previous_finished', 'time_to_stop'])

uses_instruments = ['update_sampled_contracts', 'update_historical_prices', 'update_multiple_adj_prices']
uses_fx_codes = ['update_fx_prices']



data = dataBlob()

## get control list for methods that use instruments
## get control list for methods that use fx

def get_control_data_list_for_all_methods_as_df(data):
    cd_list = get_control_data_list_for_all_methods(data)
    pdf = make_df_from_list_of_named_tuple(dataForMethod, cd_list)
    pdf = pdf.sort_values('last_run_or_heartbeat')
    return pdf

def get_control_data_list_for_all_processes_as_df(data):
    cd_list = get_control_data_list_for_all_processes(data)
    pdf = make_df_from_list_of_named_tuple(dataForProcess, cd_list)
    pdf = pdf.transpose()

    return pdf


def get_control_data_list_for_all_processes(data):
    all_processes = get_list_of_all_processes(data)
    list_of_control_data = [get_control_data_for_process_name(data, process_name)
                            for process_name in all_processes]

    return list_of_control_data

def get_control_data_for_process_name(data, process_name):
    data_control = dataControlProcess(data)
    diag_process_config = diagProcessConfig(data)

    control_data = data_control.get_dict_of_control_processes()
    control_data_for_process = control_data[process_name]

    all_config = diag_process_config.get_config_dict(process_name)

    time_to_run = diag_process_config.is_it_time_to_run(process_name)
    previous_finished = diag_process_config.has_previous_process_finished_in_last_day(process_name)
    time_to_stop = diag_process_config.is_it_time_to_stop(process_name)
    right_machine = diag_process_config.is_this_correct_machine(process_name)


    data_for_process = dataForProcess(name = process_name, running = control_data_for_process.currently_running,
                                      start = control_data_for_process.last_start_time.strftime(short_date_string),
                                      end = control_data_for_process.last_end_time.strftime(short_date_string),
                                      status = control_data_for_process.status,
                                      finished_in_last_day=control_data_for_process.has_process_finished_in_last_day(),
                                      start_time = all_config['start_time'],
                                      end_time = all_config['end_time'],
                                      required_machine= all_config['machine_name'],
                                      previous_required = all_config['previous_process'],
                                      right_machine = right_machine,
                                      time_to_run = time_to_run,
                                      time_to_stop = time_to_stop,
                                      previous_finished=previous_finished)

    return data_for_process

dataForMethod = namedtuple("dataForMethod", ['method_or_strategy','process_name', 'last_run_or_heartbeat'])


def get_control_data_list_for_all_methods(data):
    list_one = get_control_data_list_for_ordinary_methods(data)
    list_two = get_control_data_list_for_strategy_processes(data)

    all_list = list_one + list_two

    return all_list

def get_control_data_list_for_ordinary_methods(data):
    all_methods_and_processes = get_method_names_and_process_names(data)
    list_of_controls = [get_control_data_for_single_ordinary_method(data, method_name_and_process) for \
                        method_name_and_process in all_methods_and_processes]
    return list_of_controls

def get_control_data_for_single_ordinary_method(data, method_name_and_process):
    method, process_name = method_name_and_process
    last_run_or_heartbeat = get_last_run_or_heartbeat(data, dict(type = method))

    data_for_method = dataForMethod(method_or_strategy=method, process_name=process_name, last_run_or_heartbeat=last_run_or_heartbeat)

    return data_for_method

short_date_string = '%m/%d %H:%M'

def get_last_run_or_heartbeat(data, attr_dict):
    log_data = accessLogFromMongodb(data.mongo_db)
    last_run_or_heartbeat = log_data.find_last_entry_date(attr_dict)
    if last_run_or_heartbeat is missing_data:
        last_run_or_heartbeat = "00/00 Never run"
    else:
        last_run_or_heartbeat = last_run_or_heartbeat.strftime(short_date_string)

    return last_run_or_heartbeat

def get_control_data_list_for_strategy_processes(data):
    log_data = accessLogFromMongodb(data.mongo_db)
    list_of_processes = get_process_with_strategies(data)
    list_of_strategies = get_list_of_strategies()
    all_cd_list = []
    for process_name in list_of_processes:
        for strategy_name in list_of_strategies:
            last_run_or_heartbeat = get_last_run_or_heartbeat(data, dict(type=process_name, strategy_name = strategy_name))
            data_for_method = dataForMethod(method_or_strategy=strategy_name, process_name=process_name,
                                        last_run_or_heartbeat=last_run_or_heartbeat)
            all_cd_list.append(data_for_method)
    return all_cd_list

def get_method_names_and_process_names(data):
    all_methods_dict = get_methods_dict(data)
    method_and_process_list = []
    for process_name in all_methods_dict.keys():
        methods_this_process =list(all_methods_dict.get(process_name).keys())
        methods_and_process_this_process = [(method_name, process_name) for method_name in methods_this_process]
        method_and_process_list = method_and_process_list + methods_and_process_this_process

    return method_and_process_list

def get_list_of_all_processes(data):
    ordinary_process_names = get_ordinary_process_list(data)
    process_with_strategies = get_process_with_strategies(data)
    all_process_names = ordinary_process_names + process_with_strategies

    return all_process_names

def get_ordinary_process_list(data):
    all_methods_dict = get_methods_dict(data)
    ordinary_process_names = list(all_methods_dict.keys())

    return ordinary_process_names

def get_process_with_strategies(data):
    diag_process_config = diagProcessConfig(data)
    process_with_strategies = diag_process_config.get_list_of_processes_run_over_strategies()
    return process_with_strategies

def get_methods_dict(data):
    diag_process_config = diagProcessConfig(data)
    all_methods_dict = diag_process_config.get_process_configuration_for_item_name("methods")

    return all_methods_dict


if missing_data:
    pass