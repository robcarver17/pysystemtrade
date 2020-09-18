from syscore.genutils import run_interactive_menu, get_and_convert, print_menu_and_get_response
from sysdata.production.override import override_dict, Override

from sysproduction.data.get_data import dataBlob
from sysproduction.data.controls import diagOverrides, updateOverrides, dataTradeLimits, diagProcessConfig, dataControlProcess
from sysproduction.data.prices import get_valid_instrument_code_from_user
from sysproduction.data.strategies import get_valid_strategy_name_from_user, get_list_of_strategies
from sysproduction.diagnostic.emailing import retrieve_and_delete_stored_messages

def interactive_controls():
    with dataBlob(log_name = "Interactive-Controls") as data:
        menu =  run_interactive_menu(top_level_menu_of_options, nested_menu_of_options,
                                                     exit_option = -1, another_menu = -2)
    still_running = True
    while still_running:
        option_chosen = menu.propose_options_and_get_input()
        if option_chosen ==-1:
            print("FINISHED")
            return None
        if option_chosen == -2:
            continue

        method_chosen = dict_of_functions[option_chosen]
        method_chosen(data)

top_level_menu_of_options = {0:'Trade limits', 1:'Trade control (override)', 2:'Process control and monitoring'}

nested_menu_of_options = {
                    0:{0: 'View trade limits',
                       1: 'Change/add global trade limit for instrument',
                       2: 'Reset global trade limit for instrument',
                       3: 'Change/add trade limit for instrument & strategy',
                       4: 'Reset trade limit for instrument & strategy'
                    },

                    1: {10: 'View overrides',
                        11: 'Update / add / remove override for strategy',
                        12: 'Update / add / remove override for instrument',
                        13: 'Update / add / remove override for strategy & instrument'
                        },
                    2: {20: 'View process controls and status',
                        21: 'Change status of process control (STOP/GO/NO RUN)',
                        22: 'View process configuration (set in YAML, cannot change here)',
                        23: 'Mark process as finished',
                        24: 'Retrieve stored email messages'
                        }}



def view_trade_limits(data):
    trade_limits = dataTradeLimits(data)
    all_limits = trade_limits.get_all_limits()
    print("All limits\n")
    for limit in all_limits:
        print(limit)
    print("\n")

def change_limit_for_instrument(data):
    trade_limits = dataTradeLimits(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    period_days = get_and_convert("Period of days?", type_expected=int, allow_default=True, default_value = 1)
    new_limit = get_and_convert("Limit (in contracts?)", type_expected=int, allow_default=False)
    ans = input("Update will change number of trades allowed in periods, but won't reset 'clock'. Are you sure? (y/other)")
    if ans =="y":
        trade_limits.update_instrument_limit_with_new_limit(instrument_code, period_days, new_limit)

def reset_limit_for_instrument(data):
    trade_limits = dataTradeLimits(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    period_days = get_and_convert("Period of days?", type_expected=int, allow_default=True, default_value = 1)
    ans = input("Reset means trade 'clock' will restart. Are you sure? (y/other)")
    if ans =="y":
        trade_limits.reset_instrument_limit(instrument_code, period_days)

def change_limit_for_instrument_strategy(data):
    trade_limits = dataTradeLimits(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    period_days = get_and_convert("Period of days?", type_expected=int, allow_default=True, default_value = 1)
    strategy_name = get_valid_strategy_name_from_user()
    new_limit = get_and_convert("Limit (in contracts?)", type_expected=int, allow_default=False)

    ans = input("Update will change number of trades allowed in periods, but won't reset 'clock'. Are you sure? (y/other)")
    if ans =="y":
        trade_limits.update_instrument_strategy_limit_with_new_limit(strategy_name, instrument_code, period_days, new_limit)

def reset_limit_for_instrument_strategy(data):
    trade_limits = dataTradeLimits(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    period_days = get_and_convert("Period of days?", type_expected=int, allow_default=True, default_value = 1)
    strategy_name = get_valid_strategy_name_from_user()

    ans = input("Reset means trade 'clock' will restart. Are you sure? (y/other)")
    if ans =="y":
        trade_limits.reset_instrument_strategy_limit(strategy_name, instrument_code, period_days)

def view_overrides(data):
    diag_overrides = diagOverrides(data)
    all_overrides = diag_overrides.get_dict_of_all_overrides()
    print("All overrides:\n")
    for key, item in all_overrides.items():
        print("%s %s" % (key, str(item)))
    print("\n")

def update_strategy_override(data):
    update_overrides = updateOverrides(data)
    strategy_name = get_valid_strategy_name_from_user()
    new_override = get_overide_object_from_user()
    ans = input("Are you sure? (y/other)")
    if ans =="y":
        update_overrides.update_override_for_strategy(strategy_name, new_override)


def update_instrument_override(data):
    update_overrides = updateOverrides(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    new_override = get_overide_object_from_user()
    ans = input("Are you sure? (y/other)")
    if ans =="y":
        update_overrides.update_override_for_instrument(instrument_code, new_override)

def update_strategy_instrument_override(data):
    update_overrides = updateOverrides(data)
    instrument_code = get_valid_instrument_code_from_user(data)
    strategy_name = get_valid_strategy_name_from_user()
    new_override = get_overide_object_from_user()
    ans = input("Are you sure? (y/other)")
    if ans =="y":
        update_overrides.update_override_for_strategy_instrument(strategy_name, instrument_code, new_override)


def get_overide_object_from_user():
    invalid_input = True
    while invalid_input:
        print("Overide options are: A number between 0.0 and 1.0 that we multiply the natural position by,")
        print("   or one of the following special values %s" % override_dict)

        value = input("Your value?")
        value = float(value)
        try:
            override_object = Override.from_float(value)
            return override_object
        except Exception as e:
            print(e)

def view_process_controls(data):
    dict_of_controls = get_dict_of_process_controls(data)
    print("\nControlled processes:\n")
    for key,value in dict_of_controls.items():
        print("%s: %s" % (str(key), str(value)))
    return dict_of_controls

def get_dict_of_process_controls(data):
    data_process = dataControlProcess(data)
    dict_of_controls = data_process.get_dict_of_control_processes()

    return dict_of_controls

def change_process_control_status(data):
    data_process = dataControlProcess(data)
    process_name = get_process_name(data)
    status_int = print_menu_and_get_response({1:"Go", 2:"Do not run (don't stop if already running)", 3:"Stop (and don't run if not started)"}, default_option=0, default_str="<CANCEL>")
    if status_int==1:
        data_process.change_status_to_go(process_name)
    if status_int==2:
        data_process.change_status_to_no_run(process_name)
    if status_int==3:
        data_process.change_status_to_stop(process_name)

    return None

def get_process_name(data):
    process_names = get_dict_of_process_controls(data)
    menu_of_options = dict(list(enumerate(process_names)))
    print("Process name?")
    option = print_menu_and_get_response(menu_of_options, default_option=1)
    ans = menu_of_options[option]
    return ans

def view_process_config(data):
    diag_config = diagProcessConfig(data)
    process_name = get_process_name(data)
    result_dict = diag_config.get_config_dict(process_name)
    for key,value in result_dict.items():
        print("%s: %s" % (str(key), str(value)))
    print("\nAbove should be modified in private_config.yaml files")

def view_strategy_config(data):
    diag_config = diagProcessConfig(data)
    strategy_name = get_valid_strategy_name_from_user()
    result_dict = diag_config.get_strategy_dict_for_strategy(strategy_name)
    for key,value in result_dict.items():
        print("%s: %s" % (str(key), str(value)))
    print("\nAbove should be modified in private_config.yaml files")


def finish_process(data):
    print("Will need to use if process aborted without properly closing")
    process_name = get_process_name(data)
    data_control = dataControlProcess(data)
    data_control.finish_process(process_name)

def retrieve_emails(data):
    subject = get_and_convert("Subject of emails (copy from emails)?",
                              type_expected=str, allow_default=True, default_value=None)
    messages = retrieve_and_delete_stored_messages(data, subject=subject)
    for msg in messages:
        print(msg)

def not_defined(data):
    print("\n\nFunction not yet defined\n\n")


dict_of_functions = {0: view_trade_limits,
                         1: change_limit_for_instrument,
                     2: reset_limit_for_instrument,
                     3: change_limit_for_instrument_strategy,
                     4: reset_limit_for_instrument_strategy,

                     10: view_overrides,
                     11: update_strategy_override,
                     12: update_instrument_override,
                     13: update_strategy_instrument_override,

                     20: view_process_controls,
                     21: change_process_control_status,
                     22: view_process_config,
                     23: finish_process,
                     24: retrieve_emails}

