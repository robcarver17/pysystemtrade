import numpy as np

from syscore.interactive import get_and_convert, run_interactive_menu, print_menu_and_get_response
from sysobjects.production.override import override_dict, Override
from sysobjects.production.tradeable_object import instrumentStrategy

from sysdata.data_blob import dataBlob
from sysproduction.data.controls import (
    diagOverrides,
    updateOverrides,
    dataTradeLimits,
    dataPositionLimits,
    dataBrokerClientIDs
)
from sysproduction.data.control_process import dataControlProcess, diagControlProcess
from sysproduction.data.prices import get_valid_instrument_code_from_user, get_list_of_instruments
from sysproduction.data.strategies import get_valid_strategy_name_from_user
from sysproduction.data.positions import diagPositions
from sysproduction.utilities.risk_metrics import get_risk_data_for_instrument

# could get from config, but might be different by system
MAX_VS_AVERAGE_FORECAST = 2.0

def interactive_controls():
    with dataBlob(log_name="Interactive-Controls") as data:
        menu = run_interactive_menu(
            top_level_menu_of_options,
            nested_menu_of_options,
            exit_option=-1,
            another_menu=-2,
        )
    still_running = True
    while still_running:
        option_chosen = menu.propose_options_and_get_input()
        if option_chosen == -1:
            print("FINISHED")
            return None
        if option_chosen == -2:
            continue

        method_chosen = dict_of_functions[option_chosen]
        method_chosen(data)


top_level_menu_of_options = {
    0: "Trade limits",
    1: "Position limits",
    2: "Trade control (override)",
    3: "Broker client IDS",
    4: "Process control and monitoring",
}

nested_menu_of_options = {
    0: {
        0: "View trade limits",
        1: "Change/add global trade limit for instrument",
        2: "Reset global trade limit for instrument",
        3: "Change/add trade limit for instrument & strategy",
        4: "Reset trade limit for instrument & strategy",
        5: "Reset all trade limits",
        6: "Auto populate trade limits"
    },
    1: {
        10: "View position limits",
        11: "Change position limit for instrument",
        12: "Change position limit for instrument & strategy",
        13: "Auto populate position limits"
    },
    2: {
        20: "View overrides",
        21: "Update / add / remove override for strategy",
        22: "Update / add / remove override for instrument",
        23: "Update / add / remove override for strategy & instrument",
    },
    3: {
        30: "Clear all unused client IDS"
    },
    4: {
        40: "View process controls and status",
        41: "Change status of process control (STOP/GO/NO RUN)",
        42: "Global status change  (STOP/GO/NO RUN)",
        43: "Mark process as finished",
        44: "Mark all dead processes as finished",
        45: "View process configuration (set in YAML, cannot change here)",
    },
}


def view_trade_limits(data):
    trade_limits = dataTradeLimits(data)
    all_limits = trade_limits.get_all_limits_sorted()
    print("All limits\n")
    for limit in all_limits:
        print(limit)
    print("\n")


def change_limit_for_instrument(data):
    trade_limits = dataTradeLimits(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    period_days = get_and_convert(
        "Period of days?",
        type_expected=int,
        allow_default=True,
        default_value=1)
    new_limit = get_and_convert(
        "Limit (in contracts?)", type_expected=int, allow_default=False
    )
    ans = input(
        "Update will change number of trades allowed in periods, but won't reset 'clock'. Are you sure? (y/other)"
    )
    if ans == "y":
        trade_limits.update_instrument_limit_with_new_limit(
            instrument_code, period_days, new_limit
        )



def reset_limit_for_instrument(data):
    trade_limits = dataTradeLimits(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    period_days = get_and_convert(
        "Period of days?",
        type_expected=int,
        allow_default=True,
        default_value=1)
    ans = input(
        "Reset means trade 'clock' will restart. Are you sure? (y/other)")
    if ans == "y":
            trade_limits.reset_instrument_limit(instrument_code, period_days)

def reset_all_limits(data):
    trade_limits = dataTradeLimits(data)
    ans = input(
        "Reset means trade 'clock' will restart. Are you sure? (y/other)")
    if ans == "y":
        trade_limits.reset_all_limits()



def change_limit_for_instrument_strategy(data):
    trade_limits = dataTradeLimits(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    strategy_name = get_valid_strategy_name_from_user(data)
    period_days = get_and_convert(
        "Period of days?",
        type_expected=int,
        allow_default=True,
        default_value=1)
    new_limit = get_and_convert(
        "Limit (in contracts?)", type_expected=int, allow_default=False
    )

    ans = input(
        "Update will change number of trades allowed in periods, but won't reset 'clock'. Are you sure? (y/other)"
    )
    if ans == "y":
        instrument_strategy = instrumentStrategy(instrument_code=instrument_code, strategy_name=strategy_name)
        trade_limits.update_instrument_strategy_limit_with_new_limit(
            instrument_strategy=instrument_strategy, period_days=period_days, new_limit=new_limit
        )


def reset_limit_for_instrument_strategy(data):
    trade_limits = dataTradeLimits(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    period_days = get_and_convert(
        "Period of days?",
        type_expected=int,
        allow_default=True,
        default_value=1)
    strategy_name = get_valid_strategy_name_from_user(data=data, source="positions")

    ans = input(
        "Reset means trade 'clock' will restart. Are you sure? (y/other)")
    if ans == "y":
        instrument_strategy = instrumentStrategy(instrument_code=instrument_code, strategy_name=strategy_name)
        trade_limits.reset_instrument_strategy_limit(
            instrument_strategy=instrument_strategy, period_days=period_days
        )



def auto_populate_limits(data: dataBlob):
    instrument_list = get_list_of_instruments(data)
    risk_multiplier, max_leverage = get_risk_multiplier_and_max_leverage()
    trade_multiplier = get_and_convert("Higgest proportion of standard position expected to trade daily?",
                                       type_expected=float, default_value=0.33)
    period_days = get_and_convert("What period in days to set limit for?", type_expected=int, default_value=1)
    _ = [set_trade_limit_for_instrument(data, instrument_code=instrument_code,
                                        risk_multiplier=risk_multiplier,
                                        trade_multiplier=trade_multiplier,
                                        period_days=period_days,
                                        max_leverage = max_leverage)
                        for instrument_code in instrument_list]
    return None

def set_trade_limit_for_instrument(data,
                                   instrument_code: str,
                                   risk_multiplier: float,
                                   trade_multiplier: float,
                                   period_days: int,
                                   max_leverage: float):

    trade_limits = dataTradeLimits(data)
    new_limit = calc_trade_limit_for_instrument(data,
                                                instrument_code=instrument_code,
                                                risk_multiplier=risk_multiplier,
                                                trade_multiplier=trade_multiplier,
                                                max_leverage = max_leverage,
                                                period_days=period_days)
    if np.isnan(new_limit):
        print("Can't calculate trade limit for %s, not setting" % instrument_code)
    else:
        print("Update limit for %s %d with %d" % (instrument_code, period_days, new_limit))
        trade_limits.update_instrument_limit_with_new_limit(
            instrument_code, period_days, new_limit)


def calc_trade_limit_for_instrument(data: dataBlob,
                                    instrument_code: str,
                                    risk_multiplier: float,
                                    trade_multiplier: float,
                                    period_days: int,
                                    max_leverage: float):
    standard_position = get_standardised_position(data,
                                                  instrument_code= instrument_code,
                                                  risk_multiplier=risk_multiplier,
                                                  max_leverage=max_leverage)
    if np.isnan(standard_position):
        return np.nan

    adj_trade_multiplier = (float(period_days)**.5) * trade_multiplier
    standard_trade = float(standard_position) * adj_trade_multiplier
    standard_trade_int = max(4, int(np.ceil(abs(standard_trade))))

    return standard_trade_int

def get_risk_multiplier_and_max_leverage() -> (float, float):
    print("Enter parameters to estimate typical position sizes")
    notional_risk_target = get_and_convert("Notional risk target (% per year)", type_expected=float, default_value=.25)
    approx_IDM = get_and_convert("Approximate IDM", type_expected=float, default_value=2.5)
    notional_instrument_weight = get_and_convert("Notional instrument weight (go large for safety!)",
                                                 type_expected=float, default_value=.1)
    raw_max_leverage = get_and_convert("Maximum Leverage per instrument (notional exposure*# contracts / capital)",
                                   type_expected=float,
                                   default_value=1.0)
    # because we multiply by eg 2, need to half this
    max_leverage = raw_max_leverage / MAX_VS_AVERAGE_FORECAST

    risk_multiplier = notional_risk_target * approx_IDM * notional_instrument_weight

    return  risk_multiplier, max_leverage




def get_standardised_position(data: dataBlob, instrument_code: str,
                              risk_multiplier: float,
                            max_leverage: float = 1.0
                              )-> float:


    risk_data = get_risk_data_for_instrument(data, instrument_code)
    position_for_risk = get_standardised_position_for_risk(risk_data, risk_multiplier)
    position_with_leverage = get_maximum_position_given_leverage_limit(risk_data, max_leverage)

    standard_position = min(position_for_risk, position_with_leverage)

    print("Standardised position for %s is %f, minimum of %f (risk) and %f (leverage)" % (instrument_code,
                                                                                          standard_position,
                                                                                          position_for_risk,
                                                                                          position_with_leverage))

    return standard_position

def get_standardised_position_for_risk(risk_data: dict, risk_multiplier: float
                              ) -> int:

    capital = risk_data['capital']
    annual_risk_per_contract = risk_data['annual_risk_per_contract']

    annual_risk_target = capital * risk_multiplier
    standard_position = annual_risk_target / annual_risk_per_contract

    return abs(standard_position)

def get_maximum_position_given_leverage_limit(risk_data: dict, leverage_limit: float = 1.0) -> float:
    notional_exposure_per_contract = risk_data['contract_exposure']
    max_exposure = risk_data['capital'] * leverage_limit

    return abs(max_exposure / notional_exposure_per_contract)

def view_position_limit(data):

    data_position_limits = dataPositionLimits(data)
    instrument_limits = data_position_limits.get_all_instrument_limits_and_positions()
    strategy_instrument_limits = data_position_limits.get_all_strategy_instrument_limits_and_positions()

    print("\nInstrument limits across strategies\n")
    for limit_tuple in instrument_limits:
        print(limit_tuple)

    print("\nInstrument limits per strategy\n")
    for limit_tuple in strategy_instrument_limits:
        print(limit_tuple)



def change_position_limit_for_instrument(data):
    view_position_limit(data)
    data_position_limits = dataPositionLimits(data)
    instrument_code = get_valid_instrument_code_from_user(data, allow_all=False)
    new_position_limit = get_and_convert("New position limit?", type_expected=int, allow_default=True,
                                         default_str="No limit", default_value=-1)
    if new_position_limit==-1:
        data_position_limits.delete_position_limit_for_instrument(instrument_code)
    else:
        new_position_limit = abs(new_position_limit)
        data_position_limits.set_abs_position_limit_for_instrument(instrument_code, new_position_limit)


def change_position_limit_for_instrument_strategy(data):
    view_position_limit(data)
    data_position_limits = dataPositionLimits(data)
    strategy_name = get_valid_strategy_name_from_user(data, allow_all=False, source="positions")
    instrument_code = get_valid_instrument_code_from_user(data, allow_all=False)
    new_position_limit = get_and_convert("New position limit?", type_expected=int, allow_default=True,
                                         default_value=-1, default_str = "No limit")

    instrument_strategy = instrumentStrategy(instrument_code=instrument_code,
                                             strategy_name=strategy_name)

    if new_position_limit==-1:
        data_position_limits.delete_position_limit_for_instrument_strategy(instrument_strategy)
    else:
        new_position_limit = abs(new_position_limit)
        data_position_limits.set_position_limit_for_instrument_strategy(instrument_strategy, new_position_limit)

def auto_populate_position_limits(data: dataBlob):
    instrument_list = get_list_of_instruments(data)
    risk_multiplier, max_leverage = get_risk_multiplier_and_max_leverage()
    [set_position_limit_for_instrument(data,
                                       instrument_code=instrument_code,
                                       risk_multiplier=risk_multiplier,
                                       max_leverage=max_leverage)
                        for instrument_code in instrument_list]
    return None

def set_position_limit_for_instrument(data,
                                      instrument_code: str,
                                      risk_multiplier: float,
                                      max_leverage: float):

    data_position_limits = dataPositionLimits(data)
    max_position_int = get_max_position_for_instrument(data,
                                                       instrument_code=instrument_code,
                                                       risk_multiplier=risk_multiplier,
                                                       max_leverage=max_leverage)

    if np.isnan(max_position_int):
        print("Can't get standard position for %s, not setting max position" % instrument_code)
    else:
        print("Update limit for %s with %d" % (instrument_code, max_position_int))
        data_position_limits.set_abs_position_limit_for_instrument( instrument_code, max_position_int)

def get_max_position_for_instrument(data,
                                    instrument_code: str,
                                    risk_multiplier: float,
                                    max_leverage: float):

    standard_position = get_standardised_position(data,
                                                  instrument_code=instrument_code,
                                                  risk_multiplier=risk_multiplier,
                                                  max_leverage=max_leverage)
    if np.isnan(standard_position):
        return np.nan

    max_position = MAX_VS_AVERAGE_FORECAST*standard_position
    max_position_int = max(1, int(np.ceil(abs(max_position))))

    return max_position_int

def view_overrides(data):
    diag_overrides = diagOverrides(data)
    all_overrides = diag_overrides.get_dict_of_all_overrides()
    print("All overrides:\n")
    for key, item in all_overrides.items():
        print("%s %s" % (key, str(item)))
    print("\n")


def update_strategy_override(data):
    view_overrides(data)
    update_overrides = updateOverrides(data)
    strategy_name = get_valid_strategy_name_from_user(data=data, source="positions")
    new_override = get_overide_object_from_user()
    ans = input("Are you sure? (y/other)")
    if ans == "y":
        update_overrides.update_override_for_strategy(
            strategy_name, new_override)


def update_instrument_override(data):
    view_overrides(data)
    update_overrides = updateOverrides(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    new_override = get_overide_object_from_user()
    ans = input("Are you sure? (y/other)")
    if ans == "y":
        update_overrides.update_override_for_instrument(
            instrument_code, new_override)


def update_strategy_instrument_override(data):
    view_overrides(data)
    update_overrides = updateOverrides(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    strategy_name = get_valid_strategy_name_from_user(data=data, source="positions")
    instrument_strategy = instrumentStrategy(instrument_code=instrument_code, strategy_name=strategy_name)
    new_override = get_overide_object_from_user()
    ans = input("Are you sure? (y/other)")
    if ans == "y":
        update_overrides.update_override_for_instrument_strategy(
            instrument_strategy=instrument_strategy, new_override=new_override
        )


def get_overide_object_from_user():
    invalid_input = True
    while invalid_input:
        print(
            "Overide options are: A number between 0.0 and 1.0 that we multiply the natural position by,"
        )
        print("   or one of the following special values %s" % override_dict)

        value = input("Your value?")
        value = float(value)
        try:
            override_object = Override.from_numeric_value(value)
            return override_object
        except Exception as e:
            print(e)


def clear_used_client_ids(data):
    print("Clear all locks on broker client IDs. DO NOT DO IF ANY BROKER SESSIONS ARE ACTIVE!")
    ans = input("Are you sure? (y/other)")
    if ans == "y":
        client_id_data = dataBrokerClientIDs(data)
        client_id_data.clear_all_clientids()


def view_process_controls(data):
    dict_of_controls = get_dict_of_process_controls(data)
    print("\nControlled processes:\n")
    print(dict_of_controls)


def get_dict_of_process_controls(data):
    data_process = dataControlProcess(data)
    dict_of_controls = data_process.get_dict_of_control_processes()

    return dict_of_controls


def change_process_control_status(data):
    view_process_controls(data)

    process_name = get_process_name(data)
    status_int= get_valid_status_for_process()
    change_process_given_int(data, process_name, status_int)
    return None

def change_global_process_control_status(data):
    view_process_controls(data)
    print("Status for *all* processes")
    status_int= get_valid_status_for_process()
    if status_int ==0:
        return None
    process_dict = get_dict_of_process_controls(data)
    process_list = list(process_dict.keys())
    for process_name in process_list:
        change_process_given_int(data, process_name, status_int)

def get_valid_status_for_process():
    status_int = print_menu_and_get_response(
        {
            1: "Go",
            2: "Do not run (don't stop if already running)",
            3: "Stop (and don't run if not started)",
            4: "Pause (carry on running process, but don't run methods)"
        },
        default_option=0,
        default_str="<CANCEL>",
    )
    return status_int

def change_process_given_int(data, process_name, status_int):
    data_process = dataControlProcess(data)

    if status_int == 1:
        data_process.change_status_to_go(process_name)
    if status_int == 2:
        data_process.change_status_to_no_run(process_name)
    if status_int == 3:
        data_process.change_status_to_stop(process_name)
    if status_int == 4:
        data_process.change_status_to_pause(process_name)


def get_process_name(data):
    process_names = get_dict_of_process_controls(data)
    menu_of_options = dict(list(enumerate(process_names)))
    print("Process name?")
    option = print_menu_and_get_response(menu_of_options, default_option=1)
    ans = menu_of_options[option]
    return ans


def view_process_config(data):
    diag_config = diagControlProcess(data)
    process_name = get_process_name(data)
    result_dict = diag_config.get_config_dict(process_name)
    for key, value in result_dict.items():
        print("%s: %s" % (str(key), str(value)))
    print("\nAbove should be modified in private_config.yaml files")



def finish_process(data):
    view_process_controls(data)
    print("Will need to use if process aborted without properly closing")
    process_name = get_process_name(data)
    data_control = dataControlProcess(data)
    data_control.finish_process(process_name)

def finish_all_processes(data):
    data_control = dataControlProcess(data)
    data_control.check_if_pid_running_and_if_not_finish_all_processes()



def not_defined(data):
    print("\n\nFunction not yet defined\n\n")


dict_of_functions = {
    0: view_trade_limits,
    1: change_limit_for_instrument,
    2: reset_limit_for_instrument,
    3: change_limit_for_instrument_strategy,
    4: reset_limit_for_instrument_strategy,
    5: reset_all_limits,
    6: auto_populate_limits,
    10: view_position_limit,
    11: change_position_limit_for_instrument,
    12: change_position_limit_for_instrument_strategy,
    13: auto_populate_position_limits,
    20: view_overrides,
    21: update_strategy_override,
    22: update_instrument_override,
    23: update_strategy_instrument_override,
    30: clear_used_client_ids,
    40: view_process_controls,
    41: change_process_control_status,
    42: change_global_process_control_status,
    43: finish_process,
    44: finish_all_processes,
    45: view_process_config,
}

