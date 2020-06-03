"""
Interactive tool to do the following:

Look at the instrument, order and broker stack
Do standard things to the instrument, order and broker stack (normally automated)
Put in a fill for an existing order that wasn't picked up from IB


FIX ME FUTURE:

- check IB for fills (would also happen automatically)
- cancel an order on the stack
- manual trade: create an instrument and contract trades, put on the stack for IB to execute
- balance trade: create an instrument and contract trades and fill them immediately with a manual fill to match a missing older IB order
- allow an order to be modified and propagated

"""

import datetime

from sysbrokers.IB.ibConnection import connectionIB
from sysbrokers.IB.ibFuturesContractPriceData import get_instrument_object_from_config
from syscore.dateutils import get_datetime_input
from syscore.genutils import get_and_convert, print_menu_and_get_response

from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob
from sysproduction.data.positions import diagPositions
from syslogdiag.log import logToMongod as logger

from sysexecution.instrument_to_contract_stack_handler import instrument_to_contract_stack_handler


menu_of_options = {0: 'Exit',
                   1: 'View instrument order stack',
                   2: 'View contract order stack',
                   3: 'Spawn contract orders from instrument orders',
                   4: 'Create force roll orders',
                   5: 'Manually fill contract order',
                   6: 'Pass fills upwards',
                   7: 'Handle completed orders',
                   8: 'Lock/unlock order',
                   9: 'View positions'}



def update_order_stack():
    with mongoDb() as mongo_db,\
        logger("Update-Order-Stack", mongo_db=mongo_db) as log:

            data = dataBlob(mongo_db = mongo_db, log = log)

            stack_handler = instrument_to_contract_stack_handler(data)

            still_running = True
            while still_running:
                option_chosen = print_menu_and_get_response(menu_of_options, default_option=0)
                if option_chosen ==0:
                    print("FINISHED")
                    return None

                method_chosen = dict_of_functions[option_chosen]
                method_chosen(stack_handler)


def generate_manual_contract_fill(stack_handler):
    print("Manually fill a contract order. Use only if no broker order has been generated.")
    order_id = get_and_convert("Enter contract order ID", default_str="Cancel", default_value="")
    if order_id=="":
        return None
    try:
        order = stack_handler.contract_stack.get_order_with_id_from_stack(order_id)
        print("Order now %s" % str(order))
        # FIX ME HANDLE SPREAD ORDERS
        fill_qty = get_and_convert("Quantity to fill (must be less than or equal to %s)"
                                   % str(order.trade), type_expected=int, allow_default=True,
                                   default_value=order.trade)
        if type(fill_qty) is int:
            fill_qty = [fill_qty]
        filled_price = get_and_convert("Filled price", type_expected=float, allow_default=False)
        fill_datetime  =get_datetime_input("Fill datetime", allow_default=True)

        stack_handler.contract_stack.manual_fill_for_contract_id(order_id,
                                                                 fill_qty, filled_price=filled_price,
                                                                 fill_datetime=fill_datetime)
        order = stack_handler.contract_stack.get_order_with_id_from_stack(order_id)

        print("Order now %s" % str(order))
        print("If stack process not running, your next job will be to pass fills upwards")

    except Exception as e:
        print("%s went wrong!" % e)


def view_instrument_stack(stack_handler):
    order_ids = stack_handler.instrument_stack.get_list_of_order_ids()
    print("\nINSTRUMENT STACK \n")
    for order_id in order_ids:
        print(stack_handler.instrument_stack.get_order_with_id_from_stack(order_id).terse_repr())


def view_contract_stack(stack_handler):
    order_ids = stack_handler.contract_stack.get_list_of_order_ids()
    print("\nCONTRACT STACK \n")

    for order_id in order_ids:
        order = stack_handler.contract_stack.get_order_with_id_from_stack(order_id)
        IB_code = get_instrument_object_from_config(order.instrument_code).meta_data['symbol']
        print("%s:%s" % (IB_code, order.terse_repr()))

def spawn_contracts_from_instrument_orders(stack_handler):
    print("This will create contract orders for any instrument orders that don't have them")
    ans = input("Are you sure? (Y/other)")
    if ans !="Y":
        return None
    try:
        ans = get_and_convert("Which instrument order ID", default_value="ALL", default_str="All", type_expected=int)
        if ans =="ALL":
            stack_handler.spawn_children_from_new_instrument_orders()
        else:
            instrument_order_id = int(ans)
            stack_handler.spawn_children_from_instrument_order_id(instrument_order_id)
    except Exception as e:
            print("Something went wrong! %s" % e)

    print("If you are trading manually, you should now view the contract order stack and trade.")
    print("Then create manual fills for contract orders")

def pass_fills_upwards(stack_handler):
    print("This will process any fills applied to child orders")
    ans = input("Are you sure? (Y/other)")
    if ans !="Y":
        return None
    contract_order_id = get_and_convert("Which order ID?", default_value="ALL", default_str="for all", type_expected=int)
    try:
        if contract_order_id=="ALL":
            stack_handler.pass_fills_from_children_up_to_parents()
        else:
            stack_handler.apply_contract_fill_to_parent_order(contract_order_id)

    except Exception as e:
        print("Something went wrong! %s" % e)

    print("If stack process not running, your next job will be to handle completed orders")


def generate_force_roll_orders(stack_handler):
    print("This will generate force roll orders")
    ans = input("Are you sure? (Y/other)")
    if ans != "Y":
        return None
    ans = input("Which instrument? <RETURN for default: All>")
    try:
        if ans == "":
            stack_handler.generate_force_roll_orders()
        else:
            stack_handler.generate_force_roll_orders_for_instrument(ans)
    except Exception as e:
        print("Something went wrong! %s" % e)


def handle_completed_orders(stack_handler):
    print("This will process any completed orders (all fills present)")
    ans = input("Are you sure? (Y/other)")
    if ans != "Y":
        return None
    try:
        instrument_order_id = get_and_convert("Which instrument order ID?", default_str="All", default_value="ALL",
                              type_expected=int)
        if instrument_order_id == "ALL":
            stack_handler.handle_completed_orders()
        else:
            stack_handler.handle_completed_instrument_order(instrument_order_id)

    except Exception as e:
        print("Something went wrong! %s" % e)

def order_locking(stack_handler):

    ans = get_and_convert("Contract stack [1] or instrument stack [2]?", type_expected=int,
                          default_str="Exit", default_value=0)
    if ans==1:
        stack = stack_handler.contract_stack
    elif ans==2:
        stack = stack_handler.instrument_stack
    else:
        return None

    try:
        order_id = get_and_convert("Order ID ", type_expected=int, allow_default=False)
        order = stack.get_order_with_id_from_stack(order_id)
        print(order)

        if order.is_order_locked():
            ans = input("Unlock order? <y/other>")
            if ans =="y":
                stack._unlock_order_on_stack(order_id)
            else:
                return None

        else:
            ans = input("Lock order? <y/other>")
            if ans =="y":
                stack._lock_order_on_stack(order_id)
            else:
                return None
    except:
        pass

    return None

def view_positions(stack_handler):
    data = stack_handler.data
    diag_positions = diagPositions(data)
    ans1=diag_positions.get_all_current_instrument_positions_as_df()
    ans2 = diag_positions.get_all_current_contract_positions_as_df()
    print("Strategy positions")
    print(ans1)
    print("\n Contract level positions")
    print(ans2)
    return None

dict_of_functions = {1: view_instrument_stack,
                     2: view_contract_stack,
                     3: spawn_contracts_from_instrument_orders,
                     4: generate_force_roll_orders,
                     5: generate_manual_contract_fill,
                     6: pass_fills_upwards,
                     7: handle_completed_orders,
                     8: order_locking,
                     9: view_positions}
