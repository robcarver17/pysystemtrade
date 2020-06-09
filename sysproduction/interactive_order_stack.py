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

from syscore.dateutils import get_datetime_input
from syscore.genutils import get_and_convert, run_interactive_menu

from sysproduction.data.get_data import dataBlob
from sysproduction.data.positions import diagPositions
from sysproduction.data.broker import dataBroker

from sysexecution.instrument_to_contract_stack_handler import instrument_to_contract_stack_handler



def interactive_order_stack():
    with dataBlob(log_name = "Interactive-Order-Stack") as data:
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

top_level_menu_of_options = {0:'View', 1:'Create contract orders', 2:'Fills and completions',
                3:'Modify/cancel'}

nested_menu_of_options = {
                    0:{0: 'View specific order',
                   1: 'View instrument order stack',
                   2: 'View contract order stack',
                    3: 'View positions'},

                    1: {

                   10: 'Spawn contract orders from instrument orders',
                   11: 'Create force roll orders'},
                    2: {
                   20: 'Manually fill contract order',
                   21: 'Pass fills upwards',
                   22: 'Handle completed orders'},
                    3: {
                   30: 'Modify or cancel instrument order',
                   31: 'Pass modification from instrument to contract',
                   32: 'Complete modification for contract',
                   33: 'Pass modification complete from contract to instrument',
                   34: 'Clear completed modifications',
                    35: 'Lock/unlock order'}}


def generate_manual_contract_fill(data):
    stack_handler = instrument_to_contract_stack_handler(data)
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


def view_instrument_stack(data):
    stack_handler = instrument_to_contract_stack_handler(data)

    order_ids = stack_handler.instrument_stack.get_list_of_order_ids()
    print("\nINSTRUMENT STACK \n")
    for order_id in order_ids:
        print(stack_handler.instrument_stack.get_order_with_id_from_stack(order_id).terse_repr())


def view_contract_stack(data):
    stack_handler = instrument_to_contract_stack_handler(data)

    order_ids = stack_handler.contract_stack.get_list_of_order_ids()
    print("\nCONTRACT STACK \n")
    broker_data = dataBroker(data)
    for order_id in order_ids:
        order = stack_handler.contract_stack.get_order_with_id_from_stack(order_id)
        IB_code = broker_data.get_brokers_instrument_code(order.instrument_code)
        print("%s:%s" % (IB_code, order.terse_repr()))

def spawn_contracts_from_instrument_orders(data):
    stack_handler = instrument_to_contract_stack_handler(data)

    print("This will create contract orders for any instrument orders that don't have them")

    try:
        order_id = get_and_convert("Which instrument order ID", default_value="ALL", default_str="All", type_expected=int)
        check_ans = input("Are you sure? (Y/other)")
        if check_ans != "Y":
            return None
        if order_id =="ALL":
            stack_handler.spawn_children_from_new_instrument_orders()
        else:
            stack_handler.spawn_children_from_instrument_order_id(order_id)
    except Exception as e:
            print("Something went wrong! %s" % e)

    print("If you are trading manually, you should now view the contract order stack and trade.")
    print("Then create manual fills for contract orders")

def pass_fills_upwards(data):
    stack_handler = instrument_to_contract_stack_handler(data)

    print("This will process any fills applied to child orders")
    contract_order_id = get_and_convert("Which order ID?", default_value="ALL", default_str="for all", type_expected=int)
    ans = input("Are you sure? (Y/other)")
    if ans !="Y":
        return None
    try:
        if contract_order_id=="ALL":
            stack_handler.pass_fills_from_children_up_to_parents()
        else:
            stack_handler.apply_contract_fill_to_parent_order(contract_order_id)

    except Exception as e:
        print("Something went wrong! %s" % e)

    print("If stack process not running, your next job will be to handle completed orders")


def generate_force_roll_orders(data):
    stack_handler = instrument_to_contract_stack_handler(data)

    print("This will generate force roll orders")
    instrument_code = input("Which instrument? <RETURN for default: All instruments>")
    ans = input("Are you sure? (Y/other)")
    if ans != "Y":
        return None
    try:
        if instrument_code == "":
            stack_handler.generate_force_roll_orders()
        else:
            stack_handler.generate_force_roll_orders_for_instrument(instrument_code)
    except Exception as e:
        print("Something went wrong! %s" % e)


def handle_completed_orders(data):
    stack_handler = instrument_to_contract_stack_handler(data)

    print("This will process any completed orders (all fills present)")
    try:
        instrument_order_id = get_and_convert("Which instrument order ID?", default_str="All", default_value="ALL",
                              type_expected=int)
        ans = input("Are you sure? (Y/other)")
        if ans != "Y":
            return None

        if instrument_order_id == "ALL":
            stack_handler.handle_completed_orders()
        else:
            stack_handler.handle_completed_instrument_order(instrument_order_id)

    except Exception as e:
        print("Something went wrong! %s" % e)

def order_view(data):
    stack = resolve_stack(data)
    if stack is None:
        return None
    order_id = get_and_convert("Order ID?", type_expected=int, allow_default=False)
    order = stack.get_order_with_id_from_stack(order_id)
    print("%s" % order)

    return None

def order_locking(data):
    stack = resolve_stack(data)
    if stack is None:
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

def resolve_stack(data):
    stack_handler = instrument_to_contract_stack_handler(data)

    ans = get_and_convert("Contract stack [1] or instrument stack [2]?", type_expected=int,
                          default_str="Exit", default_value=0)
    if ans==1:
        stack = stack_handler.contract_stack
    elif ans==2:
        stack = stack_handler.instrument_stack
    else:
        return None
    return stack

def view_positions(data):
    data_broker = dataBroker(data)

    diag_positions = diagPositions(data)
    ans1=diag_positions.get_all_current_strategy_instrument_positions()
    ans2 = diag_positions.get_all_current_contract_positions()
    ans3 = data_broker.get_all_current_contract_positions()
    print("Strategy positions")
    print(ans1)
    print("\n Contract level positions")
    print(ans2)
    breaks = diag_positions.get_list_of_breaks_between_contract_and_strategy_positions()
    if len(breaks)>0:
        print("\nBREAKS between strategy and contract positions: %s\n" % str(breaks))
    else:
        print("(No breaks positions consistent)")
    print("\n Broker positions")
    print(ans3)
    breaks = data_broker.get_list_of_breaks_between_broker_and_db_contract_positions()
    if len(breaks)>0:
        print("\nBREAKS between broker and DB stored contract positions: %s\n" % str(breaks))
    else:
        print("(No breaks positions consistent)")
    return None

def modify_instrument_order(data):
    stack_handler = instrument_to_contract_stack_handler(data)

    order_id = get_and_convert("Enter order ID", type_expected=int, default_str="Cancel", default_value=0)
    if order_id ==0:
        return None
    try:
        order = stack_handler.instrument_stack.get_order_with_id_from_stack(order_id)
        print("Existing order %s" % str(order))
        new_qty = get_and_convert("New quantity (zero to cancel)", type_expected=int, default_value = order.trade)
        stack_handler.instrument_stack.modify_order_on_stack(order_id, new_qty)
        print("You will probably want to push modifications down to contract orders next, if not running on auto")
    except Exception as e:
        print("%s went wrong!" % e)

def pass_modifications_down_to_contracts(data):
    print("This will pass a parent instrument order modification downwards")
    stack_handler = instrument_to_contract_stack_handler(data)

    try:
        order_id = get_and_convert("Which instrument order ID", default_value="ALL", default_str="All", type_expected=int)
        check_ans = input("Are you sure? (Y/other)")
        if check_ans != "Y":
            return None
        if order_id =="ALL":
            stack_handler.pass_on_modification_from_instrument_to_contract_orders()
        else:
            stack_handler.pass_modification_from_parent_to_children(order_id)
    except Exception as e:
            print("Something went wrong! %s" % e)

    print("If you are trading manually, you will now want to mark contract modifications as complete")

def complete_modification_for_contract(data):
    stack_handler = instrument_to_contract_stack_handler(data)

    try:
        order_id = get_and_convert("Which contract order ID", default_value=0, default_str="CANCEL", type_expected=int)
        if order_id ==0:
            return None
        else:
            stack_handler.contract_stack.completed_modifying_order_on_stack(order_id)
    except Exception as e:
            print("Something went wrong! %s" % e)

    print("If you are trading manually, you will now want to pass the modification complete from contract to instruments")


def pass_on_modification_complete_from_contract_to_instrument_orders(data):
    print("This will mark all orders ")
    stack_handler = instrument_to_contract_stack_handler(data)

    try:
        order_id = get_and_convert("Which contract order ID", default_value="ALL", default_str="All", type_expected=int)
        check_ans = input("Are you sure? (Y/other)")
        if check_ans != "Y":
            return None
        if order_id =="ALL":
            stack_handler.pass_on_modification_from_instrument_to_contract_orders()
        else:
            stack_handler.pass_modification_complete_from_child_to_parent_orders(order_id)
    except Exception as e:
            print("Something went wrong! %s" % e)

    print("If you are trading manually, you will now want to clear modifications")

def clear_completed_modifications_from_instrument_and_contract_stacks(data):
    stack_handler = instrument_to_contract_stack_handler(data)

    ans = input("Clear all completed modifications from instrument and contract stacks, sure? (Y/other")
    if ans =="Y":
        try:
            stack_handler.clear_completed_modifications_from_instrument_and_contract_stacks()
        except Exception as e:
            print("%s went wrong")

    return None


dict_of_functions = {0: order_view,
                         1: view_instrument_stack,
                     2: view_contract_stack,
3: view_positions,
                     10: spawn_contracts_from_instrument_orders,
                     11: generate_force_roll_orders,
                     20: generate_manual_contract_fill,
                     21: pass_fills_upwards,
                     22: handle_completed_orders,

                     30: modify_instrument_order,
                     31: pass_modifications_down_to_contracts,
                     32: complete_modification_for_contract,
                     33: pass_on_modification_complete_from_contract_to_instrument_orders,
                     34: clear_completed_modifications_from_instrument_and_contract_stacks,
                    35: order_locking}
