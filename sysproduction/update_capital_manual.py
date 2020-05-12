
import datetime

from sysbrokers.IB.ibConnection import connectionIB

from syscore.objects import success, failure,  missing_data, arg_not_supplied

from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob
from sysproduction.data.capital import dataCapital
from syslogdiag.log import logToMongod as logger


def update_capital_manual():
    """
    Interactive session that allows you to manipulate capital manually

    :return: Nothing
    """
    with mongoDb() as mongo_db,\
        logger("Update-Capital-Manual", mongo_db=mongo_db) as log,\
        connectionIB(mongo_db = mongo_db, log=log.setup(component="IB-connection")) as ib_conn:

        data = dataBlob(mongo_db = mongo_db, log = log, ib_conn = ib_conn)

        data_capital = dataCapital(data)

        still_running = True
        while still_running:
            # display capital and get input
            user_option_int = print_capital_and_get_user_input(data_capital)
            if user_option_int==0:
                setup_initial_capital(data_capital)
            elif user_option_int==1:
                update_capital_from_ib(data_capital)
            elif user_option_int==2:
                adjust_capital_for_delta(data_capital)
            elif user_option_int==3:
                modify_any_value(data_capital)
            elif user_option_int==4:
                delete_capital_since_time(data_capital)
            elif user_option_int==919:
                delete_all_capital(data_capital)
            elif user_option_int==5:
                still_running=False
                break
            else:
                print("%d is not a valid option but was in list of possible options: check code" % str(user_option_int))

            ## Back to top of while loop

    return success

def print_capital_and_get_user_input(capital_data):
    invalid_input=True
    while invalid_input:
        all_calcs = capital_data.total_capital_calculator.get_all_capital_calcs()
        print("\n")
        if all_calcs is missing_data:
            ## No capital
            no_capital_setup = True
            print("No capital setup yet")
        else:
            no_capital_setup = False
            print(all_calcs.tail(10))

        print("\n")
        possible_options = [(0, '0: Setup initial capital parameters'), (1, '1: Update capital from IB account value'),
                            (2, '2: Adjust account value for withdrawal or deposit'), (3, '3: Modify any/all values'),
                            (4, '4: Delete values of capital since time T'), (919, '919: Delete everything and start again'),
                            (5, '5: Exit')]

        if no_capital_setup:
            possible_options = possible_options[:1]+possible_options[-1:]
        else:
            possible_options = possible_options[1:]

        option_keys = [x[0] for x in possible_options]
        option_strings = [x[1] for x in possible_options]

        print("\n".join(option_strings))
        user_option = input("\nWhat would you like to do?")
        try:
            user_option_int = int(user_option)
            assert user_option_int in option_keys
        except:
            input("\n%s is not a valid option: press return to continue" % str(user_option))
            continue

        invalid_input = False
        break

    return user_option_int

def setup_initial_capital(data_capital):
    broker_account_value, total_capital, maximum_capital, acc_pandl = get_initial_capital_values_from_user(data_capital)
    ans=input("Are you sure about this? Will delete all existing capital (not for individual strategies) Yes/<anything else>")
    if ans=="Yes":
        data_capital.total_capital_calculator.create_initial_capital(broker_account_value,
                                                                     total_capital=arg_not_supplied,
                                                                     maximum_capital=arg_not_supplied,
                                                                     acc_pandl=arg_not_supplied, are_you_really_sure=True)

    return success

def get_initial_capital_values_from_user(data_capital):
        broker_account_value = get_float_from_input("Broker account value (<return> for default, get from IB")
        if broker_account_value is arg_not_supplied:
            broker_account_value = data_capital.get_ib_total_capital_value()
            print("Got broker account value of %f from IB" % broker_account_value)
        total_capital = get_float_from_input("Total capital at risk (<return> for default, %f)" % broker_account_value, if_empty_return=broker_account_value)
        maximum_capital = get_float_from_input("Max capital, only used for half compounding (<return for default, %f)" % total_capital, if_empty_return = total_capital)
        acc_pandl = get_float_from_input("Accumulated profit (<return for default: 0)", if_empty_return=0.0)

        return broker_account_value, total_capital, maximum_capital, acc_pandl

def get_float_from_input(prompt, allow_empty=True, if_empty_return=arg_not_supplied):
    err_msg = "%s is not a valid input, needs to be a float"
    if allow_empty:
        err_msg = err_msg + " or <return> for default"
    invalid_input = True
    while invalid_input:
        value = input(prompt)
        if value=='':
            if allow_empty:
                return if_empty_return
        try:
            value = float(value)
        except:
            print(err_msg % str(value))
            continue

        invalid_input = False

    return value

def update_capital_from_ib(data_capital):
    broker_account_value = data_capital.get_ib_total_capital_value()
    try:
        total_capital = data_capital.total_capital_calculator.\
            get_total_capital_with_new_broker_account_value(broker_account_value, check_limit=0.1)
    except:
        ans = input("Do you want to try again, without checking for large capital changes? Yes/<anything else>")
        if ans=="Yes":
            total_capital = data_capital.total_capital_calculator. \
                get_total_capital_with_new_broker_account_value(broker_account_value, check_limit=9999)
        else:
            return failure

    print("New total capital is %s" % total_capital)

def adjust_capital_for_delta(data_capital):
    capital_delta = get_float_from_input("What change have you made to brokerage account that will not change capital +ve deposit, -ve withdrawal", allow_empty=False)
    old_capital = data_capital.capital_data.get_current_total_capital()
    new_capital = old_capital + capital_delta
    ans = input("New brokerage capital will be %f, are you sure? Yes/<anything else for no>"% new_capital)
    if ans=='Yes':
        data_capital.total_capital_calculator.adjust_broker_account_for_delta(capital_delta)
    else:
        return failure

    return success

def modify_any_value(data_capital):
    broker_account_value, total_capital, maximum_capital, acc_pandl = get_values_from_user_to_modify()
    ans = input("Sure about this? May cause subtle weirdness in capital calculations? Yes/<anything else>")
    if ans=="Yes":
        data_capital.total_capital_calculator.modify_account_values(broker_account_value=broker_account_value,
                                                                    total_capital=total_capital,
                                                                    maximum_capital=maximum_capital,
                                                                    acc_pandl=acc_pandl)
    else:
        return failure

    return success

def get_values_from_user_to_modify():
    broker_account_value = get_float_from_input("Broker account value (<return> for default, unchanged")
    total_capital = get_float_from_input("Total capital at risk (<return> for default, unchanged)")
    maximum_capital = get_float_from_input("Max capital, only used for half compounding (<return for default, unchanged)")
    acc_pandl = get_float_from_input("Accumulated profit (<return for default: 0)", if_empty_return=0.0)

    return broker_account_value, total_capital, maximum_capital, acc_pandl


def delete_capital_since_time(data_capital):
    print("Delete capital from when?")
    start_date = get_datetime_input()
    ans = input("Are you sure about this? Can't be undone Yes/<other for no>")
    if ans=="Yes":
        data_capital.total_capital_calculator.delete_recent_capital(start_date, are_you_sure=True)
    else:
        return failure

    return success

def get_datetime_input():
    invalid_input = True
    while invalid_input:
        ans = input("Enter date and time in format %Y%-%m-%d eg '2020-05-30' OR '%Y-%m-%d %H:%M:%S' eg '2020-05-30 14:04:11'")
        try:
            if len(ans)==10:
                ans = datetime.datetime.strptime(ans, "%Y-%m-%d")
            elif len(ans)==19:
                ans = datetime.datetime.strptime(ans, "%Y-%m-%d %H:%M:%S")
            else:
                ## problems formatting will also raise value error
                raise ValueError
            invalid_input=False
            break

        except ValueError:
            print("%s is not a valid datetime string" % ans)
            continue

    return ans

def delete_all_capital(data_capital):
    ans = input("Will delete all capital history (though not for individual strategies). Really sure this is a good idea? Can't be recovered from: Yes/<anything else for no>")
    if ans=="Yes":
        try:
            result = data_capital.total_capital_calculator.delete_all_capital(are_you_really_sure=True)
            return success
        except:
            print("Something went wrong: You may have to manually drop collection in mongo DB")
            return failure
    return failure

