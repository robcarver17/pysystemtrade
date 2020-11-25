from syscore.dateutils import get_datetime_input
from syscore.genutils import (
    run_interactive_menu,
    print_menu_of_values_and_get_response,
    get_and_convert,
    print_menu_and_get_response,
)
from syscore.pdutils import set_pd_print_options
from syscore.objects import user_exit, arg_not_supplied
from sysexecution.base_orders import listOfOrders

from sysdata.data_blob import dataBlob

from sysproduction.data.backtest import dataBacktest
from sysproduction.data.capital import dataCapital
from sysproduction.data.contracts import (
    get_valid_instrument_code_and_contractid_from_user,
    diagContracts, get_valid_contract_object_from_user
)
from sysproduction.data.currency_data import currencyData, get_valid_fx_code_from_user
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.logs import diagLogs
from sysproduction.data.orders import dataOrders
from sysproduction.data.positions import diagPositions, dataOptimalPositions
from sysproduction.data.prices import get_valid_instrument_code_from_user, diagPrices
from sysproduction.data.strategies import get_valid_strategy_name_from_user

from sysproduction.diagnostic.emailing import retrieve_and_delete_stored_messages
from sysproduction.diagnostic.reporting import run_report
from sysproduction.diagnostic.rolls import ALL_ROLL_INSTRUMENTS
from sysproduction.diagnostic.strategies import ALL_STRATEGIES
from sysproduction.diagnostic.report_configs import (
    roll_report_config,
    daily_pandl_report_config,
    status_report_config,
    trade_report_config,
    reconcile_report_config,
    strategy_report_config,
    risk_report_config
)


def interactive_diagnostics():
    print("\n\n INTERACTIVE DIAGONSTICS\n\n")
    set_pd_print_options()
    with dataBlob(log_name="Interactive-Diagnostics") as data:
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
    0: "backtest objects",
    1: "reports",
    2: "logs, emails, and errors",
    3: "View prices",
    4: "View capital",
    5: "View positions & orders",
    6: "View instrument configuration",
}

nested_menu_of_options = {0: {1: "Interactive python",
                              2: "Plot method",
                              3: "Print method",
                              4: "HTML output"},
                          1: {10: "Roll report",
                              11: "P&L report",
                              12: "Status report",
                              13: "Trade report",
                              14: "Reconcile report",
                              15: "Strategy report",
                              16: "Risk report"
                              },
                          2: {20: "View stored emails",
                              21: "View errors",
                              22: "View logs"},
                          3: {30: "Individual futures contract prices",
                              31: "Multiple prices",
                              32: "Adjusted prices",
                              33: "FX prices",
                              },
                          4: {40: "Capital for an individual strategy",
                              41: "Total capital: current capital",
                              42: "Total capital: broker account valuation",
                              43: "Total capital: maximum capital",
                              44: "Total capital: accumulated returns",
                              },
                          5: {50: "Optimal position history (instruments for strategy)",
                              51: "Actual position history (instruments for strategy)",
                              52: "Actual position history (contracts for instrument)",
                              53: "List of historic instrument level orders (for strategy)",
                              54: "List of historic contract level orders (for strategy and instrument)",
                              55: "List of historic broker level orders (for strategy and instrument)",
                              56: "View individual order",
                              },
                          6: {60: "View instrument configuration data",
                              61: "View contract configuration data",
                              },
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


# reports
def roll_report(data):
    instrument_code = get_valid_instrument_code_from_user(data, allow_all=True, all_code=ALL_ROLL_INSTRUMENTS)
    report_config = email_or_print(roll_report_config)
    report_config.modify_kwargs(instrument_code=instrument_code)
    run_report(report_config, data=data)


def pandl_report(data):
    start_date, end_date, calendar_days = get_report_dates(data)
    report_config = email_or_print(daily_pandl_report_config)
    report_config.modify_kwargs(
        calendar_days_back=calendar_days,
        start_date=start_date,
        end_date=end_date)
    run_report(report_config, data=data)


def status_report(data):
    report_config = email_or_print(status_report_config)
    run_report(report_config, data=data)


def trade_report(data):
    start_date, end_date, calendar_days = get_report_dates(data)
    report_config = email_or_print(trade_report_config)
    report_config.modify_kwargs(
        calendar_days_back=calendar_days,
        start_date=start_date,
        end_date=end_date)
    run_report(report_config, data=data)


def reconcile_report(data):
    report_config = email_or_print(reconcile_report_config)
    run_report(report_config, data=data)


def strategy_report(data):

    strategy_name = get_valid_strategy_name_from_user(
        data=data, allow_all=True, all_code = ALL_STRATEGIES
    )
    if strategy_name != ALL_STRATEGIES:
        data_backtests = dataBacktest(data)
        timestamp = data_backtests.interactively_choose_timestamp(
            strategy_name)
    else:
        timestamp = arg_not_supplied

    report_config = email_or_print(strategy_report_config)
    report_config.modify_kwargs(
        strategy_name=strategy_name,
        timestamp=timestamp)
    run_report(report_config, data=data)

def risk_report(data):
    report_config = email_or_print(risk_report_config)
    run_report(report_config, data=data)


def email_or_print(report_config):
    ans = get_and_convert(
        "1: Email or 2: print?",
        type_expected=int,
        allow_default=True,
        default_str="Print",
        default_value=2,
    )
    if ans == 1:
        report_config = report_config.new_config_with_modified_output("email")
    else:
        report_config = report_config.new_config_with_modified_output(
            "console")

    return report_config


def get_report_dates(data):
    end_date = get_datetime_input("End date for report?\n", allow_default=True)
    start_date = get_datetime_input(
        "Start date for report? (SPACE to use an offset from end date)\n",
        allow_no_arg=True,
    )
    if start_date is None:
        start_date = arg_not_supplied
        calendar_days = get_and_convert(
            "Calendar days back from %s?" % str(end_date),
            type_expected=int,
            allow_default=True,
            default_value=1,
        )

    else:
        calendar_days = arg_not_supplied

    return start_date, end_date, calendar_days


# logs emails errors
def retrieve_emails(data):
    subject = get_and_convert(
        "Subject of emails (copy from emails)?",
        type_expected=str,
        allow_default=True,
        default_value=None,
    )
    messages = retrieve_and_delete_stored_messages(data, subject=subject)
    for msg in messages:
        print(msg)


def view_errors(data):
    diag_logs = diagLogs(data)
    msg_levels = diag_logs.get_possible_log_level_mapping()
    print("This will get all log messages with a given level of criticality")
    print("Use view logs to filter by log attributes")
    lookback_days = get_and_convert(
        "How many days?", type_expected=int, default_value=7
    )
    print("Which level of error/message?")
    log_level = print_menu_and_get_response(msg_levels)
    log_item_list = diag_logs.get_log_items_with_level(
        log_level, attribute_dict=dict(), lookback_days=lookback_days
    )
    print_log_items(log_item_list)


def view_logs(data):
    diag_logs = diagLogs(data)
    lookback_days = get_and_convert(
        "How many days?", type_expected=int, default_value=7
    )
    attribute_dict = build_attribute_dict(diag_logs, lookback_days)
    log_item_list = diag_logs.get_log_items(
        attribute_dict=attribute_dict, lookback_days=lookback_days
    )
    print(log_item_list)


def print_log_items(log_item_list):
    for log_item in log_item_list:
        print(str(log_item) + "\n")


def build_attribute_dict(diag_logs, lookback_days):
    attribute_dict = {}
    not_finished = True
    while not_finished:
        print("Attributes selected so far %s" % str(attribute_dict))
        list_of_attributes = diag_logs.get_list_of_unique_log_attribute_keys(
            attribute_dict=attribute_dict, lookback_days=lookback_days
        )
        print("Which attribute to filter by?")
        attribute_name = print_menu_of_values_and_get_response(
            list_of_attributes)
        list_of_attribute_values = diag_logs.get_list_of_values_for_log_attribute(
            attribute_name, attribute_dict=attribute_dict, lookback_days=lookback_days)
        print("Which value for %s ?" % attribute_name)
        attribute_value = print_menu_of_values_and_get_response(
            list_of_attribute_values
        )
        attribute_dict[attribute_name] = attribute_value
        ans = input("Have you finished? (RETURN: No, anything else YES)")
        if not ans == "":
            not_finished = False
            break

    return attribute_dict


# prices
def individual_prices(data):
    contract = get_valid_contract_object_from_user(data, include_priced_contracts=True)
    diag_prices = diagPrices(data)
    prices = diag_prices.get_prices_for_contract_object(contract)

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
    strategy_name = print_menu_of_values_and_get_response(
        strat_list, default_str=strat_list[0]
    )
    capital_series = data_capital.get_capital_pd_series_for_strategy(
        strategy_name)
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
    strategy_name = get_valid_strategy_name_from_user(data=data)
    optimal_data = dataOptimalPositions(data)

    instrument_code_list = (
        optimal_data.get_list_of_instruments_for_strategy_with_optimal_position(
            strategy_name
        )
    )
    instrument_code = get_valid_code_from_list(instrument_code_list)
    if instrument_code is user_exit:
        return None

    data_series = optimal_data.get_optimal_position_as_df_for_strategy_and_instrument(
        strategy_name, instrument_code)
    print(data_series)
    return None


def get_valid_code_from_list(code_list):
    valid = False
    while not valid:
        print(code_list)
        ans = input("<RETURN to exit> ?")
        if ans == "":
            return user_exit
        if ans in code_list:
            return ans


def actual_instrument_position(data):
    diag_positions = diagPositions(data)

    strategy_name_list = diag_positions.get_list_of_strategies_with_positions()
    strategy_name = print_menu_of_values_and_get_response(strategy_name_list)
    if strategy_name is user_exit:
        return None

    instrument_code_list = (
        diag_positions.get_list_of_instruments_for_strategy_with_position(strategy_name))
    instrument_code = get_valid_code_from_list(instrument_code_list)
    if instrument_code is user_exit:
        return None

    pos_series = diag_positions.get_position_df_for_strategy_and_instrument(
        strategy_name, instrument_code
    )
    print(pos_series)
    return None


def actual_contract_position(data):
    diag_positions = diagPositions(data)

    instrument_code_list = diag_positions.get_list_of_instruments_with_any_position()
    instrument_code = get_valid_code_from_list(instrument_code_list)
    if instrument_code is user_exit:
        return None

    contract_code_list = (
        diag_positions.get_list_of_contracts_with_any_contract_position_for_instrument(
            instrument_code
        )
    )
    contract_code = get_valid_code_from_list(contract_code_list)
    if contract_code is user_exit:
        return None

    pos_series = diag_positions.get_position_df_for_instrument_and_contract_id(
        instrument_code, contract_code
    )
    print(pos_series)
    return None


def list_of_instrument_orders(data):
    order_pd = get_order_pd(
        data,
        list_method="get_historic_instrument_orders_in_date_range",
        getter_method="get_historic_instrument_order_from_order_id",
    )
    print(order_pd)
    return None


def get_order_pd(
    data,
    list_method="get_historic_instrument_orders_in_date_range",
    getter_method="get_historic_instrument_order_from_order_id",
):
    start_date = get_datetime_input("Start Date", allow_default=True)
    end_date = get_datetime_input("End Date", allow_default=True)

    data_orders = dataOrders(data)
    list_func = getattr(data_orders, list_method)
    getter_func = getattr(data_orders, getter_method)

    order_id_list = list_func(start_date, end_date)
    order_list = [getter_func(id) for id in order_id_list]
    order_list_object = listOfOrders(order_list)
    order_pd = order_list_object.as_pd()

    return order_pd


def list_of_contract_orders(data):
    order_pd = get_order_pd(
        data,
        list_method="get_historic_contract_orders_in_date_range",
        getter_method="get_historic_contract_order_from_order_id",
    )
    print(order_pd)
    return None


def list_of_broker_orders(data):
    order_pd = get_order_pd(
        data,
        list_method="get_historic_broker_orders_in_date_range",
        getter_method="get_historic_broker_order_from_order_id",
    )
    print(order_pd)
    return None


def view_individual_order(data):
    list_of_order_types = [
        "Instrument / Strategy",
        "Instrument / Contract",
        "Broker level",
    ]
    print("Which order queue?")
    order_type = print_menu_of_values_and_get_response(list_of_order_types)
    order_id = get_and_convert(
        "Order number?",
        type_expected=int,
        default_value=None,
        default_str="CANCEL")
    if order_id is None:
        return None

    data_orders = dataOrders(data)
    if order_type == list_of_order_types[0]:
        order = data_orders.get_historic_instrument_order_from_order_id(
            order_id)
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
    instrument_code, contract_id = get_valid_instrument_code_and_contractid_from_user(
        data)
    diag_contracts = diagContracts(data)
    contract_object = diag_contracts.get_contract_object(
        instrument_code, contract_id)
    contract_date = diag_contracts.get_contract_date_object_with_roll_parameters(
        instrument_code, contract_id)
    print(contract_object.as_dict())
    print(contract_date.roll_parameters)

    return None


dict_of_functions = {
    1: backtest_python,
    2: backtest_plot,
    3: backtest_print,
    4: backtest_html,
    10: roll_report,
    11: pandl_report,
    12: status_report,
    13: trade_report,
    14: reconcile_report,
    15: strategy_report,
    16: risk_report,
    20: retrieve_and_delete_stored_messages,
    21: view_errors,
    22: view_logs,
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
    61: view_contract_config,
}
