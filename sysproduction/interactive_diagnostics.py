import pandas as pd

from syscore.dateutils import get_datetime_input
from syscore.genutils import run_interactive_menu, print_menu_of_values_and_get_response, get_and_convert
from syscore.pdutils import set_pd_print_options
from syscore.objects import user_exit
from sysexecution.base_orders import listOfOrders

from sysproduction.data.get_data import dataBlob

from sysproduction.data.backtest import dataBacktest
from sysproduction.data.capital import dataCapital
from sysproduction.data.contracts import get_valid_instrument_code_and_contractid_from_user, diagContracts
from sysproduction.data.currency_data import currencyData, get_valid_fx_code_from_user
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.orders import dataOrders
from sysproduction.data.positions import diagPositions, dataOptimalPositions
from sysproduction.data.prices import get_valid_instrument_code_from_user, diagPrices
from sysproduction.data.strategies import get_valid_strategy_name_from_user


def interactive_diagnostics():
    print("\n\n INTERACTIVE DIAGONSTICS\n\n")
    set_pd_print_options()
    with dataBlob(log_name = "Interactive-Diagnostics") as data:
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

top_level_menu_of_options = {0:'backtest objects', 1:'reports', 2:'logs, emails, and errors',
                             3:'View prices', 4:'View capital', 5:'View positions & orders',
                             6: 'View instrument configuration'}

nested_menu_of_options = {
                    0:{
                           1: 'Interactive python',
                       2: 'Plot method',
                       3: 'Print method',
                       4: 'HTML output'
                    },

                    1: {10: 'nothing yet'
                        },
                    2: {20: 'nothing yet'
                        },
                    3: {30: 'Individual futures contract prices',
                        31: 'Multiple prices',
                        32: 'Adjusted prices',
                        33: 'FX prices'
                        },
                    4: {40: 'Capital for an individual strategy',
                        41: 'Total capital: current capital',
                        42: 'Total capital: broker account valuation',
                        43: 'Total capital: maximum capital',
                        44: 'Total capital: accumulated returns'
                        },
                    5: {50: 'Optimal position history (instruments for strategy)',
                        51: 'Actual position history (instruments for strategy)',
                        52: 'Actual position history (contracts for instrument)',
                        53: 'List of historic instrument level orders (for strategy)',
                        54: 'List of historic contract level orders (for strategy and instrument)',
                        55: 'List of historic broker level orders (for strategy and instrument)',
                        56: 'View individual order'
                        },

    6: {60: 'View instrument configuration data',
        61: 'View contract configuration data'
                            }
                        }


def not_defined(data):
    print("\n\nFunction not yet defined\n\n")


def backtest_plot(data):
    data_backtests = dataBacktest(data)
    data_backtests.plot_data_loop()
    return None

def backtest_python(data):
    data_backtests = dataBacktest(data)
    data_backtests.eval_loop()
    return None

def backtest_print(data):
    data_backtests = dataBacktest(data)
    data_backtests.print_data_loop()
    return None

def backtest_html(data):
    data_backtests = dataBacktest(data)
    data_backtests.html_data_loop()
    return None


## prices
def individual_prices(data):
    instrument_code, contract_date = get_valid_instrument_code_and_contractid_from_user(data)
    diag_prices = diagPrices(data)
    prices = diag_prices.get_prices_for_instrument_code_and_contract_date(instrument_code, contract_date)

    print(prices)

    return None


def multiple_prices(data):
    instrument_code = get_valid_instrument_code_from_user(data)
    diag_prices = diagPrices(data)
    prices = diag_prices.get_multiple_prices(instrument_code)
    print(prices)

    return None

def adjusted_prices(data):
    instrument_code = get_valid_instrument_code_from_user(data)
    diag_prices = diagPrices(data)
    prices = diag_prices.get_adjusted_prices(instrument_code)
    print(prices)

    return None

def fx_prices(data):
    fx_code = get_valid_fx_code_from_user(data)
    diag_prices = currencyData(data)
    prices = diag_prices.get_fx_prices(fx_code)
    print(prices)

    return None


def capital_strategy(data):
    data_capital = dataCapital(data)
    strat_list = data_capital.get_list_of_strategies_with_capital()
    strategy_name = print_menu_of_values_and_get_response(strat_list, default_str=strat_list[0])
    capital_series = data_capital.get_capital_pd_series_for_strategy(strategy_name)
    print(capital_series)
    return None

def total_current_capital(data):
    data_capital = dataCapital(data)
    capital_series = data_capital.get_series_of_total_capital()
    print(capital_series)
    return None

def total_broker_capital(data):
    data_capital = dataCapital(data)
    capital_series = data_capital.get_series_of_broker_capital()
    print(capital_series)
    return None

def total_max_capital(data):
    data_capital = dataCapital(data)
    capital_series = data_capital.get_series_of_maximum_capital()
    print(capital_series)
    return None

def total_acc_capital(data):
    data_capital = dataCapital(data)
    capital_series = data_capital.get_series_of_accumulated_capital()
    print(capital_series)
    return None

def optimal_positions(data):
    strategy_name = get_valid_strategy_name_from_user()
    optimal_data = dataOptimalPositions(data)

    instrument_code_list = optimal_data.get_list_of_instruments_for_strategy_with_optimal_position(strategy_name)
    instrument_code = get_valid_code_from_list(instrument_code_list)
    if instrument_code is user_exit:
        return None

    data_series = optimal_data.get_optimal_position_as_df_for_strategy_and_instrument(strategy_name, instrument_code)
    print(data_series)
    return None

def get_valid_code_from_list(code_list):
    valid = False
    while not valid:
        print(code_list)
        ans = input("<RETURN to exit> ?")
        if ans=="":
            return user_exit
        if ans in code_list:
            return ans

def actual_instrument_position(data):
    diag_positions = diagPositions(data)

    strategy_name_list = diag_positions.get_list_of_strategies_with_positions()
    strategy_name = print_menu_of_values_and_get_response(strategy_name_list)
    if strategy_name is user_exit:
        return None

    instrument_code_list = diag_positions.get_list_of_instruments_for_strategy_with_position(strategy_name)
    instrument_code = get_valid_code_from_list(instrument_code_list)
    if instrument_code is user_exit:
        return None

    pos_series = diag_positions.get_position_df_for_strategy_and_instrument(strategy_name, instrument_code)
    print(pos_series)
    return None

def actual_contract_position(data):
    diag_positions = diagPositions(data)

    instrument_code_list = diag_positions.get_list_of_instruments_with_any_position()
    instrument_code = get_valid_code_from_list(instrument_code_list)
    if instrument_code is user_exit:
        return None

    contract_code_list = diag_positions.get_list_of_contracts_with_any_contract_position_for_instrument(instrument_code)
    contract_code = get_valid_code_from_list(contract_code_list)
    if contract_code is user_exit:
        return None

    pos_series = diag_positions.get_position_df_for_instrument_and_contract_id(instrument_code, contract_code)
    print(pos_series)
    return None


def list_of_instrument_orders(data):
    order_pd = get_order_pd(data, list_method = 'get_historic_instrument_orders_in_date_range',
                 getter_method = 'get_historic_instrument_order_from_order_id')
    print(order_pd)
    return None

def get_order_pd(data, list_method = 'get_historic_instrument_orders_in_date_range',
                 getter_method = 'get_historic_instrument_order_from_order_id'):
    start_date = get_datetime_input("Start Date", allow_default = True)
    end_date = get_datetime_input("End Date", allow_default = True)

    data_orders = dataOrders(data)
    list_func = getattr(data_orders, list_method)
    getter_func  = getattr(data_orders, getter_method)

    order_id_list = list_func(start_date, end_date)
    order_list = [getter_func(id)
                  for id in order_id_list]
    order_list_object = listOfOrders(order_list)
    order_pd = order_list_object.as_pd()

    return order_pd

def list_of_contract_orders(data):
    order_pd = get_order_pd(data, list_method = 'get_historic_contract_orders_in_date_range',
                 getter_method = 'get_historic_contract_order_from_order_id')
    print(order_pd)
    return None


def list_of_broker_orders(data):
    order_pd = get_order_pd(data, list_method = 'get_historic_broker_orders_in_date_range',
                 getter_method = 'get_historic_broker_order_from_order_id')
    print(order_pd)
    return None


def view_individual_order(data):
    list_of_order_types = ['Instrument / Strategy', 'Instrument / Contract', 'Broker level']
    print("Which order queue?")
    order_type = print_menu_of_values_and_get_response(list_of_order_types)
    order_id = get_and_convert("Order number?", type_expected=int, default_value=None, default_str="CANCEL")
    if order_id is None:
        return None

    data_orders = dataOrders(data)
    if order_type == list_of_order_types[0]:
        order = data_orders.get_historic_instrument_order_from_order_id(order_id)
    elif order_type == list_of_order_types[1]:
        order = data_orders.get_historic_contract_order_from_order_id(order_id)
    elif order_type == list_of_order_types[2]:
        order = data_orders.get_historic_broker_order_from_order_id(order_id)

    print(order)

    return None

def view_instrument_config(data):
    instrument_code = get_valid_instrument_code_from_user(data)
    diag_instruments = diagInstruments(data)
    meta_data = diag_instruments.get_meta_data(instrument_code)
    print(meta_data)

    return None

def view_contract_config(data):
    instrument_code, contract_id = get_valid_instrument_code_and_contractid_from_user(data)
    diag_contracts = diagContracts(data)
    contract_object = diag_contracts.get_contract_object(instrument_code, contract_id)
    contract_date = diag_contracts.get_contract_date_object_with_roll_parameters(instrument_code, contract_id)
    print(contract_object.as_dict())
    print(contract_date.roll_parameters)

    return None




dict_of_functions = {
                    1: backtest_python,
                    2: backtest_plot,
                    3: backtest_print,
                    4: backtest_html,

                    10: not_defined,
                    20: not_defined,
                    30: individual_prices,
                    31: multiple_prices,
                    32: adjusted_prices,
                    33: fx_prices,
                    40: capital_strategy,
                    41: total_current_capital,
                    42: total_broker_capital,
                    43: total_max_capital,
                    44: total_acc_capital,
                    50: optimal_positions,
                    51: actual_instrument_position,
                    52: actual_contract_position,
                    53: list_of_instrument_orders,
                    54: list_of_contract_orders,
                    55: list_of_broker_orders,
                    56: view_individual_order,
                    60: view_instrument_config,
                    61: view_contract_config}

