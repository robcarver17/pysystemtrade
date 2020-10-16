"""
Monitor health of system by seeing when things last run

We can also check: when last adjusted prices were updated, when FX was last updated, when optimal position was
   last updated
"""
from collections import namedtuple

import datetime
import pandas as pd

from syscore.pdutils import make_df_from_list_of_named_tuple
from syscore.objects import header, table, body_text, arg_not_supplied, missing_data
from syscore.genutils import transfer_object_attributes

from sysproduction.data.get_data import dataBlob
from sysproduction.data.controls import (
    diagProcessConfig,
    dataControlProcess,
    dataTradeLimits,
    diagOverrides,
    dataLocks,
    dataPositionLimits
)
from sysproduction.data.strategies import get_list_of_strategies
from sysproduction.data.prices import get_list_of_instruments
from sysproduction.data.currency_data import get_list_of_fxcodes, currencyData
from sysproduction.data.prices import diagPrices
from sysproduction.data.positions import diagPositions, dataOptimalPositions

from sysproduction.data.logs import diagLogs


def system_status(data=arg_not_supplied):
    """
    Report on system status

    :param: data blob
    :return: list of formatted output items
    """
    if data is arg_not_supplied:
        data = dataBlob()

    results_object = get_status_report_data(data)
    formatted_output = format_status_data(results_object)

    return formatted_output


def get_status_report_data(data):

    process = get_control_data_list_for_all_processes_as_df(data)
    method = get_control_data_list_for_all_methods_as_df(data)
    price = get_last_price_updates_as_df(data)
    position = get_last_optimal_position_updates_as_df(data)
    limits = get_trade_limits_as_df(data)
    position_limits = get_position_limits_as_df(data)
    overrides = get_overrides_as_df(data)  # NOT WORKING
    locks = get_list_of_position_locks(data)


    results_object = dict(
        process=process,
        method=method,
        price=price,
        position=position,
        limits=limits,
        position_limits=position_limits,
        overrides=overrides,
        locks=locks,
    )
    return results_object


def format_status_data(results_object):
    """
    Put the results into a printable format

    :param results_dict: dict, keys are different segments
    :return:
    """

    formatted_output = []

    formatted_output.append(
        header("Status report produced on %s" % (str(datetime.datetime.now())))
    )

    table1_df = results_object["process"]
    table1 = table("Status of processses", table1_df)
    formatted_output.append(table1)

    table2_df = results_object["method"]
    table2 = table("Status of methods", table2_df)
    formatted_output.append(table2)

    table3_df = results_object["price"]
    table3 = table("Status of adjusted price / FX price collection", table3_df)
    formatted_output.append(table3)

    table4_df = results_object["position"]
    table4 = table("Status of optimal position generation", table4_df)
    formatted_output.append(table4)

    table5_df = results_object["limits"]
    table5 = table("Status of trade limits", table5_df)
    formatted_output.append(table5)

    table6_df = results_object["position_limits"]
    table6 = table("Status of position limits", table6_df)
    formatted_output.append(table6)

    table7_df = results_object["overrides"]
    table7 = table("Status of overrides", table7_df)
    formatted_output.append(table7)

    text1 = body_text(results_object["locks"])
    formatted_output.append(text1)

    formatted_output.append(header("END OF STATUS REPORT"))

    return formatted_output


dataForProcess = namedtuple(
    "dataForProcess",
    [
        "name",
        "running",
        "start",
        "end",
        "status",
        "finished_in_last_day",
        "start_time",
        "end_time",
        "required_machine",
        "right_machine",
        "time_to_run",
        "previous_required",
        "previous_finished",
        "time_to_stop",
    ],
)
dataForLimits = namedtuple(
    "dataForLimits",
    [
        "strategy_name",
        "instrument_code",
        "period_days",
        "trade_limit",
        "trades_since_last_reset",
        "trade_capacity_remaining",
        "time_since_last_reset",
    ],
)

dataForMethod = namedtuple(
    "dataForMethod", [
        "method_or_strategy", "process_name", "last_run_or_heartbeat"])

genericUpdate = namedtuple("genericUpdate", ["name", "last_update"])
dataOverride = namedtuple("dataOverride", ["name", "override"])

uses_instruments = [
    "update_sampled_contracts",
    "update_historical_prices",
    "update_multiple_adj_prices",
]
uses_fx_codes = ["update_fx_prices"]


def get_overrides_as_df(data):
    diag_overrides = diagOverrides(data)
    all_overrides = diag_overrides.get_dict_of_all_overrides()
    all_overrides_as_list = [
        dataOverride(key, value) for key, value in all_overrides.items()
    ]
    pdf = make_df_from_list_of_named_tuple(dataOverride, all_overrides_as_list)

    return pdf


def get_trade_limits_as_df(data):
    cd_list = get_list_of_trade_limits(data)
    pdf = make_df_from_list_of_named_tuple(dataForLimits, cd_list)

    return pdf


def get_list_of_trade_limits(data):
    trade_limits = dataTradeLimits(data)
    all_limits = trade_limits.get_all_limits()
    list_of_limits = [get_trade_limit_tuple(limit) for limit in all_limits]
    return list_of_limits


def get_trade_limit_tuple(element):
    tuple_object = transfer_object_attributes(dataForLimits, element)

    return tuple_object


def get_control_data_list_for_all_processes_as_df(data):
    cd_list = get_control_data_list_for_all_processes(data)
    pdf = make_df_from_list_of_named_tuple(dataForProcess, cd_list)
    pdf = pdf.transpose()

    return pdf


def get_control_data_list_for_all_methods_as_df(data):
    cd_list = get_control_data_list_for_all_methods(data)
    pdf = make_df_from_list_of_named_tuple(dataForMethod, cd_list)
    pdf = pdf.sort_values("last_run_or_heartbeat")
    return pdf


def get_last_price_updates_as_df(data):
    cd_list = get_list_of_last_price_updates(data)
    pdf = make_df_from_list_of_named_tuple(genericUpdate, cd_list)
    pdf = pdf.sort_values("last_update")

    return pdf


def get_last_optimal_position_updates_as_df(data):
    cd_list = get_list_of_last_position_updates(data)
    pdf = make_df_from_list_of_named_tuple(genericUpdate, cd_list)
    pdf = pdf.sort_values("last_update")

    return pdf


def get_list_of_last_price_updates(data):
    list_one = get_list_of_last_futures_price_updates(data)
    list_two = get_list_of_last_fx_price_updates(data)

    return list_one + list_two


def get_list_of_last_futures_price_updates(data):
    list_of_instruments = get_list_of_instruments(data)
    updates = [
        get_last_futures_price_update_for_instrument(data, instrument_code)
        for instrument_code in list_of_instruments
    ]
    return updates


def get_last_futures_price_update_for_instrument(data, instrument_code):
    diag_prices = diagPrices(data)
    px = diag_prices.get_adjusted_prices(instrument_code)
    last_timestamp = px.index[-1]
    update = genericUpdate(instrument_code, last_timestamp)

    return update


def get_list_of_last_fx_price_updates(data):
    list_of_codes = get_list_of_fxcodes(data)
    updates = [get_last_fx_price_update_for_code(
        data, fx_code) for fx_code in list_of_codes]
    return updates


def get_last_fx_price_update_for_code(data, fx_code):
    data_fx = currencyData(data)
    px = data_fx.get_fx_prices(fx_code)
    last_timestamp = px.index[-1]

    update = genericUpdate(fx_code, last_timestamp)

    return update


def get_list_of_last_position_updates(data):
    strategy_list = get_list_of_strategies(data)
    list_of_updates = []
    for strategy_name in strategy_list:
        updates_for_strategy = get_list_of_position_updates_for_strategy(
            data, strategy_name
        )
        list_of_updates = list_of_updates + updates_for_strategy

    return list_of_updates


def get_list_of_position_updates_for_strategy(data, strategy_name):
    instrument_list = get_list_of_instruments(data)
    list_of_updates = [
        get_last_position_update_for_strategy_instrument(
            data, strategy_name, instrument_code
        )
        for instrument_code in instrument_list
    ]

    list_of_updates = [
        update for update in list_of_updates if update is not None]

    return list_of_updates


def get_last_position_update_for_strategy_instrument(
    data, strategy_name, instrument_code
):
    op = dataOptimalPositions(data)
    pos_data = op.get_optimal_position_as_df_for_strategy_and_instrument(
        strategy_name, instrument_code
    )
    if pos_data is missing_data:
        return None
    last_update = pos_data.index[-1]
    key = "%s/%s" % (strategy_name, instrument_code)

    return genericUpdate(key, last_update)


def get_control_data_list_for_all_processes(data):
    all_processes = get_list_of_all_processes(data)
    list_of_control_data = [
        get_control_data_for_process_name(data, process_name)
        for process_name in all_processes
    ]

    return list_of_control_data


def get_control_data_for_process_name(data, process_name):
    data_control = dataControlProcess(data)
    diag_process_config = diagProcessConfig(data)

    control_data = data_control.get_dict_of_control_processes()
    control_data_for_process = control_data[process_name]

    all_config = diag_process_config.get_config_dict(process_name)

    time_to_run = diag_process_config.is_it_time_to_run(process_name)
    previous_finished = diag_process_config.has_previous_process_finished_in_last_day(
        process_name)
    time_to_stop = diag_process_config.is_it_time_to_stop(process_name)
    right_machine = diag_process_config.is_this_correct_machine(process_name)

    data_for_process = dataForProcess(
        name=process_name,
        running=control_data_for_process.currently_running,
        start=control_data_for_process.last_start_time.strftime(short_date_string),
        end=control_data_for_process.last_end_time.strftime(short_date_string),
        status=control_data_for_process.status,
        finished_in_last_day=control_data_for_process.has_process_finished_in_last_day(),
        start_time=all_config["start_time"],
        end_time=all_config["end_time"],
        required_machine=all_config["machine_name"],
        previous_required=all_config["previous_process"],
        right_machine=right_machine,
        time_to_run=time_to_run,
        time_to_stop=time_to_stop,
        previous_finished=previous_finished,
    )

    return data_for_process


def get_control_data_list_for_all_methods(data):
    list_one = get_control_data_list_for_ordinary_methods(data)
    list_two = get_control_data_list_for_strategy_processes(data)

    all_list = list_one + list_two

    return all_list


def get_control_data_list_for_ordinary_methods(data):
    all_methods_and_processes = get_method_names_and_process_names(data)
    list_of_controls = [
        get_control_data_for_single_ordinary_method(data, method_name_and_process)
        for method_name_and_process in all_methods_and_processes
    ]
    return list_of_controls


def get_control_data_for_single_ordinary_method(data, method_name_and_process):
    method, process_name = method_name_and_process
    last_run_or_heartbeat = get_last_run_or_heartbeat(data, dict(type=method))

    data_for_method = dataForMethod(
        method_or_strategy=method,
        process_name=process_name,
        last_run_or_heartbeat=last_run_or_heartbeat,
    )

    return data_for_method


short_date_string = "%m/%d %H:%M"


def get_last_run_or_heartbeat(data, attr_dict):
    log_data = diagLogs(data)
    last_run_or_heartbeat = log_data.find_last_entry_date(attr_dict)
    if last_run_or_heartbeat is missing_data:
        last_run_or_heartbeat = "00/00 Never run"
    else:
        last_run_or_heartbeat = last_run_or_heartbeat.strftime(
            short_date_string)

    return last_run_or_heartbeat


def get_control_data_list_for_strategy_processes(data):
    list_of_processes = get_process_with_strategies(data)
    list_of_strategies = get_list_of_strategies()
    all_cd_list = []
    for process_name in list_of_processes:
        for strategy_name in list_of_strategies:
            last_run_or_heartbeat = get_last_run_or_heartbeat(
                data, dict(type=process_name, strategy_name=strategy_name)
            )
            data_for_method = dataForMethod(
                method_or_strategy=strategy_name,
                process_name=process_name,
                last_run_or_heartbeat=last_run_or_heartbeat,
            )
            all_cd_list.append(data_for_method)
    return all_cd_list


def get_method_names_and_process_names(data):
    all_methods_dict = get_methods_dict(data)
    method_and_process_list = []
    for process_name in all_methods_dict.keys():
        methods_this_process = list(all_methods_dict.get(process_name).keys())
        methods_and_process_this_process = [
            (method_name, process_name) for method_name in methods_this_process
        ]
        method_and_process_list = (
            method_and_process_list + methods_and_process_this_process
        )

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
    process_with_strategies = (
        diag_process_config.get_list_of_processes_run_over_strategies()
    )
    return process_with_strategies


def get_methods_dict(data):
    diag_process_config = diagProcessConfig(data)
    all_methods_dict = diag_process_config.get_process_configuration_for_item_name(
        "methods")

    return all_methods_dict


def get_list_of_position_locks(data):
    data_locks = dataLocks(data)
    any_locks = data_locks.get_list_of_locked_instruments()

    return "Locked instruments (position mismatch): %s" % str(any_locks)


def get_position_limits_as_df(data):
    strat_instrument_limits_as_df = get_strategy_instrument_limits_as_df(data)
    instrument_limits_as_df = get_instrument_limits_as_df(data)

    agg_limits = pd.concat([strat_instrument_limits_as_df, instrument_limits_as_df], axis=0)

    return agg_limits

def get_strategy_instrument_limits_as_df(data):
    data_position_limits = dataPositionLimits(data)
    strat_instrument_limits = data_position_limits.get_all_strategy_instrument_limits_and_positions()
    strat_instrument_limits_as_df = df_from_list_of_limits_and_positions(strat_instrument_limits)

    return strat_instrument_limits_as_df


def get_instrument_limits_as_df(data):
    data_position_limits = dataPositionLimits(data)
    instrument_limits = data_position_limits.get_all_instrument_limits_and_positions()
    instrument_limits_as_df = df_from_list_of_limits_and_positions(instrument_limits)

    return instrument_limits_as_df


def df_from_list_of_limits_and_positions(pos_limit_list):
    keys = [pos.key for pos in pos_limit_list]
    position = [pos.position for pos in pos_limit_list]
    pos_limit = [pos.position_limit for pos in pos_limit_list]

    df = pd.DataFrame(dict(keys = keys, position = position, pos_limit = pos_limit))

    return df