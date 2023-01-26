from syscore.exceptions import missingData
from syscore.constants import arg_not_supplied, success, failure
from syscore.interactive.input import (
    get_input_from_user_and_convert_to_type,
    true_if_answer_is_yes,
)
from syscore.interactive.date_input import get_datetime_input
from syscore.interactive.menus import (
    print_menu_and_get_desired_option_index,
)

from sysdata.data_blob import dataBlob
from sysobjects.production.capital import LargeCapitalChange
from sysproduction.data.capital import dataCapital
from sysproduction.data.broker import dataBroker


def interactive_update_capital_manual():
    """
    Interactive session that allows you to manipulate capital manually

    :return: Nothing
    """
    with dataBlob(log_name="Interactive-Update-Capital-Manual") as data:

        still_running = True
        while still_running:
            # display capital and get input
            user_option_int = print_capital_and_get_user_input(data)
            function_list = [
                finished,
                setup_initial_capital,
                update_capital_from_ib,
                adjust_capital_for_delta,
                modify_any_value,
                delete_capital_since_time,
                delete_all_capital,
            ]

            try:
                function_to_run = function_list[user_option_int]
            except IndexError:
                print("%d is not a valid option" % str(user_option_int))

            function_to_run(data)

            # Back to top of while loop

    return success


def finished(data):
    exit()


def print_capital_and_get_user_input(data: dataBlob):
    data_capital = dataCapital(data)

    print("\n")
    try:
        all_calcs = data_capital.get_series_of_all_global_capital()
    except missingData:
        # No capital
        no_capital_setup = True
        print("No capital setup yet")
    else:
        no_capital_setup = False
        print(all_calcs.tail(10))

    print("\n")

    if no_capital_setup:
        possible_options = {1: "Setup initial capital parameters"}
    else:
        possible_options = {
            2: "Update capital from IB account value",
            3: "Adjust account value for withdrawal or deposit",
            4: "Modify any/all values",
            5: "Delete values of capital since time T",
            6: "Delete everything and start again",
        }

    user_option_int = print_menu_and_get_desired_option_index(
        possible_options, default_option_index=0, default_str="EXIT"
    )

    return user_option_int


def setup_initial_capital(data: dataBlob):
    (
        broker_account_value,
        total_capital,
        maximum_capital,
        acc_pandl,
    ) = get_initial_capital_values_from_user(data)
    user_agrees_to_do_this = true_if_answer_is_yes(
        "Are you *REALLY* sure about this? Will delete all existing capital (not for individual strategies)?"
    )
    if user_agrees_to_do_this:
        data_capital = dataCapital(data)
        data_capital.create_initial_capital(
            broker_account_value,
            total_capital=total_capital,
            maximum_capital=maximum_capital,
            acc_pandl=acc_pandl,
            are_you_really_sure=True,
        )


def get_initial_capital_values_from_user(data: dataBlob):
    broker_account_value = get_input_from_user_and_convert_to_type(
        "Broker account value",
        type_expected=float,
        default_value=arg_not_supplied,
        default_str="get from IB",
    )
    if broker_account_value is arg_not_supplied:
        broker_account_value = get_broker_account_value(data)
        print("Got broker account value of %f from IB" % broker_account_value)

    total_capital = get_input_from_user_and_convert_to_type(
        "Total capital at risk", type_expected=float, default_value=broker_account_value
    )

    maximum_capital = get_input_from_user_and_convert_to_type(
        "Max capital, only used for half compounding",
        type_expected=float,
        default_value=total_capital,
    )

    acc_pandl = get_input_from_user_and_convert_to_type(
        "Accumulated profit", type_expected=float, default_value=0.0
    )

    return broker_account_value, total_capital, maximum_capital, acc_pandl


A_VERY_LARGE_NUMBER = 999999999


def update_capital_from_ib(data: dataBlob):

    data_capital = dataCapital(data)
    broker_account_value = get_broker_account_value(data)
    try:
        total_capital = (
            data_capital.update_and_return_total_capital_with_new_broker_account_value(
                broker_account_value
            )
        )
        print("New total capital is %s" % total_capital)

    except LargeCapitalChange:
        ans_is_yes = true_if_answer_is_yes(
            "Do you want to try again, without checking for large capital changes??"
        )
        if ans_is_yes:
            total_capital = data_capital.update_and_return_total_capital_with_new_broker_account_value(
                broker_account_value, check_limit=A_VERY_LARGE_NUMBER
            )
        else:
            print("Capital not updated")
            return failure

    print("New total capital is %s" % str(total_capital))


def get_broker_account_value(data: dataBlob):
    data_broker = dataBroker(data)
    capital_value = data_broker.get_total_capital_value_in_base_currency()

    return capital_value


def adjust_capital_for_delta(data: dataBlob):
    data_capital = dataCapital(data)

    capital_delta = get_input_from_user_and_convert_to_type(
        "What change have you made to brokerage account that will not change capital +ve deposit, -ve withdrawal",
        type_expected=float,
    )
    effect = data_capital.return_str_with_effect_of_delta_adjustment(capital_delta)

    user_wants_adjustment = true_if_answer_is_yes("%s, are you sure? " % effect)
    if user_wants_adjustment:
        data_capital.adjust_broker_account_for_delta(capital_delta)


def modify_any_value(data: dataBlob):
    data_capital = dataCapital(data)

    (
        broker_account_value,
        total_capital,
        maximum_capital,
        acc_pandl,
    ) = get_values_from_user_to_modify(data=data)

    ans_is_yes = true_if_answer_is_yes(
        "Sure about this? May cause subtle weirdness in capital calculations?"
    )
    if ans_is_yes:
        data_capital.modify_account_values(
            broker_account_value=broker_account_value,
            total_capital=total_capital,
            maximum_capital=maximum_capital,
            acc_pandl=acc_pandl,
            are_you_sure=True,
        )


def get_values_from_user_to_modify(data: dataBlob):
    data_capital = dataCapital(data)

    current_broker_value = data_capital.get_current_broker_account_value()
    broker_account_value = get_input_from_user_and_convert_to_type(
        "Broker account value", type_expected=float, default_value=current_broker_value
    )

    current_total_capital = data_capital.get_current_total_capital()
    total_capital = get_input_from_user_and_convert_to_type(
        "Total capital at risk",
        type_expected=float,
        default_value=current_total_capital,
    )

    current_maximum_capital = data_capital.get_current_maximum_capital()
    maximum_capital = get_input_from_user_and_convert_to_type(
        "Max capital, only used for half compounding",
        type_expected=float,
        default_value=current_maximum_capital,
    )

    current_acc_profit = data_capital.get_current_accumulated_pandl()
    acc_pandl = get_input_from_user_and_convert_to_type(
        "Accumulated profit", type_expected=float, default_value=current_acc_profit
    )

    return broker_account_value, total_capital, maximum_capital, acc_pandl


def delete_capital_since_time(data: dataBlob):
    data_capital = dataCapital(data)

    last_date = get_datetime_input("Delete capital from when?")
    ans_is_yes = true_if_answer_is_yes(
        "Delete anything after %s. Are you sure about this? Can't be undone Yes/<other for no>"
        % str(last_date)
    )
    if ans_is_yes:
        data_capital.delete_recent_global_capital(last_date, are_you_sure=True)


def delete_all_capital(data: dataBlob):
    data_capital = dataCapital(data)

    ans = input(
        "Will delete all capital history (though not for individual strategies). Really sure this is a good idea? Can't be recovered from: 'YESyesYES'/<anything else for no>"
    )
    if ans == "YESyesYES":
        try:
            data_capital.delete_all_global_capital(are_you_really_sure=True)

        except BaseException:
            print(
                "Something went wrong: You may have to manually drop collection in mongo DB and corruption may have occured"
            )
    else:
        print("OK you decided not to do it")
