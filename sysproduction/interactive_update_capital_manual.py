
from syscore.objects import success, failure, missing_data, arg_not_supplied
from syscore.dateutils import get_datetime_input
from syscore.genutils import get_and_convert, print_menu_and_get_response

from sysdata.data_blob import dataBlob
from sysproduction.data.capital import dataCapital
from sysproduction.data.broker import dataBroker

def interactive_update_capital_manual():
    """
    Interactive session that allows you to manipulate capital manually

    :return: Nothing
    """
    with dataBlob(log_name="Interactive-Update-Capital-Manual") as data:

        data_capital = dataCapital(data)

        still_running = True
        while still_running:
            # display capital and get input
            user_option_int = print_capital_and_get_user_input(data_capital)
            if user_option_int == 1:
                setup_initial_capital(data)
            elif user_option_int == 2:
                update_capital_from_ib(data)
            elif user_option_int == 3:
                adjust_capital_for_delta(data_capital)
            elif user_option_int == 4:
                modify_any_value(data_capital)
            elif user_option_int == 5:
                delete_capital_since_time(data_capital)
            elif user_option_int == 919:
                delete_all_capital(data_capital)
            elif user_option_int == 0:
                still_running = False
                break
            else:
                print(
                    "%d is not a valid option but was in list of possible options: check code" %
                    str(user_option_int))

            # Back to top of while loop

    return success


def print_capital_and_get_user_input(capital_data: dataCapital):
    all_calcs = capital_data.total_capital_calculator.get_all_capital_calcs()
    print("\n")
    if all_calcs is missing_data:
        # No capital
        no_capital_setup = True
        print("No capital setup yet")
    else:
        no_capital_setup = False
        print(all_calcs.tail(10))

    print("\n")


    if no_capital_setup:
        possible_options = {
            1: "Setup initial capital parameters"}
    else:
        possible_options = {
            2: "Update capital from IB account value",
            3: "Adjust account value for withdrawal or deposit",
            4: "Modify any/all values",
            5: "Delete values of capital since time T",
            919: "Delete everything and start again"}

    user_option_int = print_menu_and_get_response(possible_options, default_option=0,
                                                  default_str="EXIT")

    return user_option_int


def setup_initial_capital(data: dataBlob):
    (
        broker_account_value,
        total_capital,
        maximum_capital,
        acc_pandl,
    ) = get_initial_capital_values_from_user(data)
    ans = input(
        "Are you sure about this? Will delete all existing capital (not for individual strategies) Yes/<anything else>"
    )
    if ans == "Yes":
        data_capital = dataCapital(data)
        data_capital.total_capital_calculator.create_initial_capital(
            broker_account_value,
            total_capital=arg_not_supplied,
            maximum_capital=arg_not_supplied,
            acc_pandl=arg_not_supplied,
            are_you_really_sure=True,
        )

    return success


def get_initial_capital_values_from_user(data: dataBlob):
    broker_account_value = get_and_convert(
        "Broker account value",
        type_expected=float,
        default_str="get from IB",
        default_value=arg_not_supplied,
    )
    if broker_account_value is arg_not_supplied:
        broker_account_value = get_broker_account_value(data)
        print("Got broker account value of %f from IB" % broker_account_value)
    total_capital = get_and_convert(
        "Total capital at risk",
        type_expected=float,
        default_value=broker_account_value)
    maximum_capital = get_and_convert(
        "Max capital, only used for half compounding",
        type_expected=float,
        default_value=total_capital,
    )
    acc_pandl = get_and_convert(
        "Accumulated profit", type_expected=float, default_value=0.0
    )

    return broker_account_value, total_capital, maximum_capital, acc_pandl


def update_capital_from_ib(data: dataBlob):
    data_capital = dataCapital(data)
    broker_account_value = get_broker_account_value(data)

    try:
        total_capital = data_capital.total_capital_calculator.get_total_capital_with_new_broker_account_value(
            broker_account_value, check_limit=0.1)
    except BaseException:
        ans = input(
            "Do you want to try again, without checking for large capital changes? Yes/<anything else>"
        )
        if ans == "Yes":
            total_capital = data_capital.total_capital_calculator.get_total_capital_with_new_broker_account_value(
                broker_account_value, check_limit=9999)
        else:
            return failure

    print("New total capital is %s" % total_capital)

def get_broker_account_value(data: dataBlob):
    data_broker = dataBroker(data)
    capital_value = data_broker.get_total_capital_value_in_base_currency()

    return capital_value

def adjust_capital_for_delta(data_capital: dataCapital):
    capital_delta = get_and_convert(
        "What change have you made to brokerage account that will not change capital +ve deposit, -ve withdrawal",
        type_expected=float,
    )
    old_capital = data_capital.capital_data.get_current_total_capital()
    new_capital = old_capital + capital_delta
    ans = input(
        "New brokerage capital will be %f, are you sure? Yes/<anything else for no>" %
        new_capital)
    if ans == "Yes":
        data_capital.total_capital_calculator.adjust_broker_account_for_delta(
            capital_delta
        )
    else:
        return failure

    return success


def modify_any_value(data_capital: dataCapital):
    (
        broker_account_value,
        total_capital,
        maximum_capital,
        acc_pandl,
    ) = get_values_from_user_to_modify()
    ans = input(
        "Sure about this? May cause subtle weirdness in capital calculations? Yes/<anything else>"
    )
    if ans == "Yes":
        data_capital.total_capital_calculator.modify_account_values(
            broker_account_value=broker_account_value,
            total_capital=total_capital,
            maximum_capital=maximum_capital,
            acc_pandl=acc_pandl,
        )
    else:
        return failure

    return success


def get_values_from_user_to_modify():
    broker_account_value = get_and_convert(
        "Broker account value",
        type_expected=float,
        default_value=arg_not_supplied,
        default_str="Unchanged",
    )
    total_capital = get_and_convert(
        "Total capital at risk",
        type_expected=float,
        default_value=arg_not_supplied,
        default_str="Unchanged",
    )
    maximum_capital = get_and_convert(
        "Max capital, only used for half compounding",
        type_expected=float,
        default_value=arg_not_supplied,
        default_str="Unchanged",
    )
    acc_pandl = get_and_convert(
        "Accumulated profit",
        type_expected=float,
        default_value=arg_not_supplied,
        default_str="Unchanged",
    )

    return broker_account_value, total_capital, maximum_capital, acc_pandl


def delete_capital_since_time(data_capital:dataCapital):
    start_date = get_datetime_input("Delete capital from when?")
    ans = input("Are you sure about this? Can't be undone Yes/<other for no>")
    if ans == "Yes":
        data_capital.total_capital_calculator.delete_recent_capital(
            start_date, are_you_sure=True
        )
    else:
        return failure

    return success


def delete_all_capital(data_capital: dataCapital):
    ans = input(
        "Will delete all capital history (though not for individual strategies). Really sure this is a good idea? Can't be recovered from: Yes/<anything else for no>"
    )
    if ans == "Yes":
        try:
            result = data_capital.total_capital_calculator.delete_all_capital(
                are_you_really_sure=True
            )
            return success
        except BaseException:
            print(
                "Something went wrong: You may have to manually drop collection in mongo DB"
            )
            return failure
    return failure
