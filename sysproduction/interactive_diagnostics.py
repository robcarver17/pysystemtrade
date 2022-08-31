import pandas as pd

from syscore.dateutils import listOfOpeningTimes
from syscore.dateutils import openingTimes
from syscore.dateutils import SECONDS_PER_HOUR
from syscore.genutils import progressBar
from syscore.interactive import get_and_convert
from syscore.interactive import get_report_dates
from syscore.interactive import print_menu_and_get_response
from syscore.interactive import print_menu_of_values_and_get_response
from syscore.interactive import run_interactive_menu
from syscore.interactive import true_if_answer_is_yes
from syscore.objects import ALL_ROLL_INSTRUMENTS
from syscore.objects import arg_not_supplied
from syscore.objects import missing_contract
from syscore.objects import user_exit
from syscore.pdutils import set_pd_print_options
from sysdata.data_blob import dataBlob
from sysexecution.orders.list_of_orders import listOfOrders
from syslogdiag.email_via_db_interface import retrieve_and_delete_stored_messages
from sysobjects.contracts import futuresContract
from sysobjects.production.tradeable_object import instrumentStrategy
from sysproduction.data.backtest import interactively_choose_timestamp
from sysproduction.data.backtest import user_choose_backtest
from sysproduction.data.broker import dataBroker
from sysproduction.data.capital import dataCapital
from sysproduction.data.contracts import dataContracts
from sysproduction.data.contracts import get_valid_contract_object_from_user
from sysproduction.data.contracts import (
    get_valid_instrument_code_and_contractid_from_user,
)
from sysproduction.data.currency_data import dataCurrency
from sysproduction.data.currency_data import get_valid_fx_code_from_user
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.logs import diagLogs
from sysproduction.data.orders import dataOrders
from sysproduction.data.positions import dataOptimalPositions
from sysproduction.data.positions import diagPositions
from sysproduction.data.prices import diagPrices
from sysproduction.data.prices import get_valid_instrument_code_from_user
from sysproduction.data.strategies import get_valid_strategy_name_from_user
from sysproduction.reporting.report_configs import account_curve_report_config
from sysproduction.reporting.report_configs import costs_report_config
from sysproduction.reporting.report_configs import daily_pandl_report_config
from sysproduction.reporting.report_configs import duplicate_market_report_config
from sysproduction.reporting.report_configs import instrument_risk_report_config
from sysproduction.reporting.report_configs import liquidity_report_config
from sysproduction.reporting.report_configs import market_monitor_report_config
from sysproduction.reporting.report_configs import min_capital_report_config
from sysproduction.reporting.report_configs import reconcile_report_config
from sysproduction.reporting.report_configs import remove_markets_report_config
from sysproduction.reporting.report_configs import risk_report_config
from sysproduction.reporting.report_configs import roll_report_config
from sysproduction.reporting.report_configs import slippage_report_config
from sysproduction.reporting.report_configs import status_report_config
from sysproduction.reporting.report_configs import strategy_report_config
from sysproduction.reporting.report_configs import trade_report_config
from sysproduction.reporting.reporting_functions import run_report
from sysproduction.reporting.strategies_report import ALL_STRATEGIES


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
    1: "View instrument configuration",
    2: "logs, emails, and errors",
    3: "View prices",
    4: "View capital",
    5: "View positions & orders",
    6: "Reports",
}

nested_menu_of_options = {
    0: {1: "Interactive python", 2: "Plot method", 3: "Print method", 4: "HTML output"},
    1: {
        10: "View instrument configuration data",
        11: "View contract configuration data",
        12: "View trading hours for all instruments",
    },
    2: {20: "View stored emails", 21: "View errors", 22: "View logs"},
    3: {
        30: "Individual futures contract prices",
        31: "Multiple prices",
        32: "Adjusted prices",
        33: "FX prices",
        34: "Spreads",
    },
    4: {
        40: "Capital for an individual strategy",
        41: "Capital for global account, all strategies",
    },
    5: {
        50: "Optimal position history (instruments for strategy)",
        51: "Actual position history (instruments for strategy)",
        52: "Actual position history (contracts for instrument)",
        53: "List of historic instrument level orders (for strategy)",
        54: "List of historic contract level orders (for strategy and instrument)",
        55: "List of historic broker level orders (for strategy and instrument)",
        56: "View individual order",
    },
    6: {
        60: "Roll report",
        61: "P&L report",
        62: "Status report",
        63: "Trade report",
        64: "Reconcile report",
        65: "Strategy report",
        66: "Risk report",
        67: "Costs report",
        68: "Slippage report",
        69: "Liquidity report",
        70: "All instrument risk",
        71: "Minimum capital required",
        72: "Duplicate markets",
        73: "Remove markets",
        74: "Market monitor",
        75: "P&L account curve",
    },
}


def not_defined(data: dataBlob):
    print("\n\nFunction not yet defined\n\n")


def backtest_plot(data: dataBlob):
    data_backtests = user_choose_backtest(data)
    data_backtests.plot_data_loop()
    return None


def backtest_python(data: dataBlob):
    data_backtests = user_choose_backtest(data)
    data_backtests.eval_loop()
    return None


def backtest_print(data: dataBlob):
    data_backtests = user_choose_backtest(data)
    data_backtests.print_data_loop()
    return None


def backtest_html(data: dataBlob):
    data_backtests = user_choose_backtest(data)
    data_backtests.html_data_loop()
    return None


# reports
def roll_report(data: dataBlob):
    instrument_code = get_valid_instrument_code_from_user(
        data, allow_all=True, all_code=ALL_ROLL_INSTRUMENTS
    )
    report_config = email_or_print_or_file(roll_report_config)
    report_config.modify_kwargs(instrument_code=instrument_code)
    run_report(report_config, data=data)


def pandl_report(data: dataBlob):
    start_date, end_date = get_report_dates()
    report_config = email_or_print_or_file(daily_pandl_report_config)
    report_config.modify_kwargs(start_date=start_date, end_date=end_date)
    run_report(report_config, data=data)


def status_report(data: dataBlob):
    report_config = email_or_print_or_file(status_report_config)
    run_report(report_config, data=data)


def trade_report(data: dataBlob):
    start_date, end_date = get_report_dates()
    report_config = email_or_print_or_file(trade_report_config)
    report_config.modify_kwargs(start_date=start_date, end_date=end_date)
    run_report(report_config, data=data)


def reconcile_report(data: dataBlob):
    report_config = email_or_print_or_file(reconcile_report_config)
    run_report(report_config, data=data)


def strategy_report(data: dataBlob):

    strategy_name = get_valid_strategy_name_from_user(
        data=data, allow_all=True, all_code=ALL_STRATEGIES
    )
    if strategy_name != ALL_STRATEGIES:
        timestamp = interactively_choose_timestamp(
            strategy_name=strategy_name, data=data
        )
    else:
        timestamp = arg_not_supplied

    report_config = email_or_print_or_file(strategy_report_config)
    report_config.modify_kwargs(strategy_name=strategy_name, timestamp=timestamp)
    run_report(report_config, data=data)


def risk_report(data: dataBlob):
    report_config = email_or_print_or_file(risk_report_config)
    run_report(report_config, data=data)


def cost_report(data: dataBlob):
    report_config = email_or_print_or_file(costs_report_config)
    run_report(report_config, data=data)


def slippage_report(data: dataBlob):
    start_date, end_date = get_report_dates()
    report_config = email_or_print_or_file(slippage_report_config)
    report_config.modify_kwargs(start_date=start_date, end_date=end_date)
    run_report(report_config, data=data)


def liquidity_report(data: dataBlob):
    report_config = email_or_print_or_file(liquidity_report_config)
    run_report(report_config, data=data)


def instrument_risk_report(data: dataBlob):
    report_config = email_or_print_or_file(instrument_risk_report_config)
    run_report(report_config, data=data)


def min_capital_report(data: dataBlob):
    report_config = email_or_print_or_file(min_capital_report_config)
    run_report(report_config, data=data)


def duplicate_market_report(data: dataBlob):
    report_config = email_or_print_or_file(duplicate_market_report_config)
    run_report(report_config, data=data)


def remove_markets_report(data: dataBlob):
    report_config = email_or_print_or_file(remove_markets_report_config)
    run_report(report_config, data=data)


def market_monitor_report(data: dataBlob):

    run_full_report = true_if_answer_is_yes(
        "Run normal full report? (alternative is customise dates)"
    )
    if run_full_report:
        start_date = arg_not_supplied
        end_date = arg_not_supplied
    else:
        start_date, end_date = get_report_dates()

    report_config = email_or_print_or_file(market_monitor_report_config)
    report_config.modify_kwargs(start_date=start_date, end_date=end_date)
    run_report(report_config, data=data)


def account_curve_report(data: dataBlob):
    run_full_report = true_if_answer_is_yes(
        "Run normal full report? (alternative is customise dates)"
    )
    if run_full_report:
        start_date = arg_not_supplied
        end_date = arg_not_supplied
    else:
        start_date, end_date = get_report_dates()

    report_config = email_or_print_or_file(account_curve_report_config)
    report_config.modify_kwargs(start_date=start_date, end_date=end_date)
    run_report(report_config, data=data)


def email_or_print_or_file(report_config):
    ans = get_and_convert(
        "1: Print or 2: email or 3: file or 4: email and file?",
        type_expected=int,
        allow_default=True,
        default_str="Print",
        default_value=1,
    )
    if ans == 1:
        report_config = report_config.new_config_with_modified_output("console")
    elif ans == 2:
        report_config = report_config.new_config_with_modified_output("email")
    elif ans == 3:
        report_config = report_config.new_config_with_modified_output("file")
    else:
        report_config = report_config.new_config_with_modified_output("emailfile")

    return report_config


# logs emails errors
def retrieve_emails(data: dataBlob):
    messages = retrieve_and_delete_stored_messages(data)
    for msg in messages:
        print(msg)


def view_errors(data: dataBlob):
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


def view_logs(data: dataBlob):
    diag_logs = diagLogs(data)
    lookback_days = get_and_convert(
        "How many days?", type_expected=int, default_value=7
    )
    attribute_dict = build_attribute_dict(diag_logs, lookback_days)
    log_item_list = diag_logs.get_log_items(
        attribute_dict=attribute_dict, lookback_days=lookback_days
    )
    print_log_items(log_item_list)


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
        attribute_name = print_menu_of_values_and_get_response(list_of_attributes)
        list_of_attribute_values = (
            diag_logs.get_unique_list_of_values_for_log_attribute(
                attribute_name,
                attribute_dict=attribute_dict,
                lookback_days=lookback_days,
            )
        )
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
def individual_prices(data: dataBlob):
    contract = get_valid_contract_object_from_user(
        data, only_include_priced_contracts=True
    )
    diag_prices = diagPrices(data)
    prices = diag_prices.get_prices_for_contract_object(contract)

    print(prices)

    return None


def multiple_prices(data: dataBlob):
    instrument_code = get_valid_instrument_code_from_user(data)
    diag_prices = diagPrices(data)
    prices = diag_prices.get_multiple_prices(instrument_code)
    print(prices)

    return None


def adjusted_prices(data: dataBlob):
    instrument_code = get_valid_instrument_code_from_user(data)
    diag_prices = diagPrices(data)
    prices = diag_prices.get_adjusted_prices(instrument_code)
    print(prices)

    return None


def fx_prices(data: dataBlob):
    fx_code = get_valid_fx_code_from_user(data)
    diag_prices = dataCurrency(data)
    prices = diag_prices.get_fx_prices(fx_code)
    print(prices)

    return None


def spreads(data: dataBlob):
    instrument_code = get_valid_instrument_code_from_user(data)
    diag_prices = diagPrices(data)
    spreads = diag_prices.get_spreads(instrument_code)

    print(spreads)

    return None


def capital_strategy(data: dataBlob):
    data_capital = dataCapital(data)
    strat_list = data_capital.get_list_of_strategies_with_capital()
    strategy_name = print_menu_of_values_and_get_response(
        strat_list, default_str=strat_list[0]
    )
    capital_series = data_capital.get_capital_pd_series_for_strategy(strategy_name)
    print(capital_series.tail(30))
    return None


def total_current_capital(data: dataBlob):
    data_capital = dataCapital(data)
    capital_series = data_capital.get_series_of_all_global_capital()
    print(capital_series.tail(30))
    return None


def optimal_positions(data: dataBlob):
    strategy_name = get_valid_strategy_name_from_user(
        data=data, source="optimal_positions"
    )
    optimal_data = dataOptimalPositions(data)

    instrument_code_list = sorted(
        optimal_data.get_list_of_instruments_for_strategy_with_optimal_position(
            strategy_name
        )
    )
    instrument_code = get_valid_code_from_list(instrument_code_list)
    if instrument_code is user_exit:
        return None
    instrument_strategy = instrumentStrategy(
        instrument_code=instrument_code, strategy_name=strategy_name
    )
    data_series: pd.DataFrame = (
        optimal_data.get_optimal_position_as_df_for_instrument_strategy(
            instrument_strategy
        )
    )
    pd.options.display.float_format = "{:,.4f}".format
    data_series.drop(columns=["position_limit_contracts"], inplace=True)
    print(data_series.columns)
    print(data_series)
    print("\n")
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


def actual_instrument_position(data: dataBlob):
    diag_positions = diagPositions(data)

    strategy_name_list = diag_positions.get_list_of_strategies_with_positions()
    strategy_name = print_menu_of_values_and_get_response(strategy_name_list)
    if strategy_name is user_exit:
        return None

    instrument_code_list = (
        diag_positions.get_list_of_instruments_for_strategy_with_position(
            strategy_name, ignore_zero_positions=False
        )
    )
    instrument_code = get_valid_code_from_list(instrument_code_list)
    if instrument_code is user_exit:
        return None
    instrument_strategy = instrumentStrategy(
        strategy_name=strategy_name, instrument_code=instrument_code
    )

    pos_series = diag_positions.get_position_df_for_instrument_strategy(
        instrument_strategy
    )
    print(pos_series)
    return None


def actual_contract_position(data: dataBlob):
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
    contract_date_str = get_valid_code_from_list(contract_code_list)
    if contract_date_str is user_exit:
        return None
    # ignore warnings can be str
    contract = futuresContract(instrument_code, contract_date_str)

    pos_series = diag_positions.get_position_df_for_contract(contract)
    print(pos_series)
    return None


def list_of_instrument_orders(data: dataBlob):
    order_pd = get_order_pd(
        data,
        list_method="get_historic_instrument_order_ids_in_date_range",
        getter_method="get_historic_instrument_order_from_order_id",
    )
    print(order_pd)
    return None


def get_order_pd(
    data,
    list_method="get_historic_instrument_order_ids_in_date_range",
    getter_method="get_historic_instrument_order_from_order_id",
):
    start_date, end_date = get_report_dates()

    data_orders = dataOrders(data)
    list_func = getattr(data_orders, list_method)
    getter_func = getattr(data_orders, getter_method)

    order_id_list = list_func(start_date, end_date)
    order_list = [getter_func(id) for id in order_id_list]
    order_list_object = listOfOrders(order_list)
    order_pd = order_list_object.as_pd()

    return order_pd


def list_of_contract_orders(data: dataBlob):
    order_pd = get_order_pd(
        data,
        list_method="get_historic_contract_order_ids_in_date_range",
        getter_method="get_historic_contract_order_from_order_id",
    )
    print(order_pd)
    return None


def list_of_broker_orders(data: dataBlob):
    order_pd = get_order_pd(
        data,
        list_method="get_historic_broker_order_ids_in_date_range",
        getter_method="get_historic_broker_order_from_order_id",
    )
    print(order_pd)
    return None


def view_individual_order(data: dataBlob):
    list_of_order_types = [
        "Instrument / Strategy",
        "Instrument / Contract",
        "Broker level",
    ]
    print("Which order queue?")
    order_type = print_menu_of_values_and_get_response(list_of_order_types)
    order_id = get_and_convert(
        "Order number?", type_expected=int, default_value=None, default_str="CANCEL"
    )
    if order_id is None:
        return None

    data_orders = dataOrders(data)
    if order_type == list_of_order_types[0]:
        order = data_orders.get_historic_instrument_order_from_order_id(order_id)
    elif order_type == list_of_order_types[1]:
        order = data_orders.get_historic_contract_order_from_order_id(order_id)
    elif order_type == list_of_order_types[2]:
        order = data_orders.get_historic_broker_order_from_order_id(order_id)
    else:
        print("Don't know what to do")
        return None

    print(order.full_repr())

    return None


def view_instrument_config(data: dataBlob):
    instrument_code = get_valid_instrument_code_from_user(data)
    diag_instruments = diagInstruments(data)
    meta_data = diag_instruments.get_meta_data(instrument_code)
    print(meta_data)
    data_broker = dataBroker(data)
    instrument_broker_data = data_broker.get_brokers_instrument_with_metadata(
        instrument_code
    )
    print(instrument_broker_data)


def view_contract_config(data: dataBlob):
    instrument_code, contract_id = get_valid_instrument_code_and_contractid_from_user(
        data
    )
    diag_contracts = dataContracts(data)
    contract_object = diag_contracts.get_contract_from_db_given_code_and_id(
        instrument_code, contract_id
    )
    contract_date = diag_contracts.get_contract_date_object_with_roll_parameters(
        instrument_code, contract_id
    )
    print(contract_object.as_dict())
    print(contract_date.roll_parameters)

    return None


def print_trading_hours_for_all_instruments(data=arg_not_supplied):
    all_trading_hours = get_trading_hours_for_all_instruments(data)
    display_a_dict_of_trading_hours(all_trading_hours)


def display_a_dict_of_trading_hours(all_trading_hours):
    for key, trading_hours_this_instrument in sorted(
        all_trading_hours.items(), key=lambda x: x[0]
    ):
        print(
            "%s: %s"
            % (
                "{:20}".format(key),
                nice_print_list_of_trading_hours(trading_hours_this_instrument),
            )
        )


MAX_WIDTH_OF_PRINTABLE_TRADING_HOURS = 3


def nice_print_list_of_trading_hours(trading_hours: listOfOpeningTimes) -> str:
    list_of_nice_str = [
        nice_print_trading_hours(trading_hour_entry)
        for trading_hour_entry in trading_hours[:MAX_WIDTH_OF_PRINTABLE_TRADING_HOURS]
    ]
    nice_string = " ".join(list_of_nice_str)
    return nice_string


def nice_print_trading_hours(trading_hour_entry: openingTimes) -> str:
    start_datetime = trading_hour_entry.opening_time
    end_datetime = trading_hour_entry.closing_time
    diff_time = end_datetime - start_datetime
    hours_in_between = (diff_time.total_seconds()) / SECONDS_PER_HOUR

    NICE_FORMAT = "%d/%m %H:%M"

    start_formatted = start_datetime.strftime(NICE_FORMAT)
    end_formatted = end_datetime.strftime(NICE_FORMAT)

    nice_string = "%s to %s (%.1f hours)" % (
        start_formatted,
        end_formatted,
        hours_in_between,
    )

    return nice_string


def get_trading_hours_for_all_instruments(data=arg_not_supplied):
    if data is arg_not_supplied:
        data = dataBlob()

    diag_prices = diagPrices(data)
    list_of_instruments = diag_prices.get_list_of_instruments_with_contract_prices()

    p = progressBar(len(list_of_instruments))
    all_trading_hours = {}
    for instrument_code in list_of_instruments:
        p.iterate()
        trading_hours = get_trading_hours_for_instrument(data, instrument_code)
        if trading_hours is missing_contract:
            print("*** NO EXPIRY FOR %s ***" % instrument_code)
            continue

        ## will have several days use first one
        check_trading_hours(trading_hours, instrument_code)
        all_trading_hours[instrument_code] = trading_hours

    p.finished()

    return all_trading_hours


def check_trading_hours(trading_hours: listOfOpeningTimes, instrument_code: str):
    for trading_hours_this_instrument in trading_hours:
        check_trading_hours_one_day(trading_hours_this_instrument, instrument_code)


def check_trading_hours_one_day(
    trading_hours_this_instrument: openingTimes, instrument_code: str
):
    if (
        trading_hours_this_instrument.opening_time
        >= trading_hours_this_instrument.closing_time
    ):
        print(
            "%s Trading hours appear to be wrong: %s"
            % (instrument_code, nice_print_trading_hours(trading_hours_this_instrument))
        )


def get_trading_hours_for_instrument(
    data: dataBlob, instrument_code: str
) -> listOfOpeningTimes:

    diag_contracts = dataContracts(data)
    contract_id = diag_contracts.get_priced_contract_id(instrument_code)

    contract = futuresContract(instrument_code, contract_id)

    data_broker = dataBroker(data)
    trading_hours = data_broker.get_trading_hours_for_contract(contract)

    return trading_hours


dict_of_functions = {
    1: backtest_python,
    2: backtest_plot,
    3: backtest_print,
    4: backtest_html,
    10: view_instrument_config,
    11: view_contract_config,
    12: print_trading_hours_for_all_instruments,
    20: retrieve_emails,
    21: view_errors,
    22: view_logs,
    30: individual_prices,
    31: multiple_prices,
    32: adjusted_prices,
    33: fx_prices,
    34: spreads,
    40: capital_strategy,
    41: total_current_capital,
    50: optimal_positions,
    51: actual_instrument_position,
    52: actual_contract_position,
    53: list_of_instrument_orders,
    54: list_of_contract_orders,
    55: list_of_broker_orders,
    56: view_individual_order,
    60: roll_report,
    61: pandl_report,
    62: status_report,
    63: trade_report,
    64: reconcile_report,
    65: strategy_report,
    66: risk_report,
    67: cost_report,
    68: slippage_report,
    69: liquidity_report,
    70: instrument_risk_report,
    71: min_capital_report,
    72: duplicate_market_report,
    73: remove_markets_report,
    74: market_monitor_report,
    75: account_curve_report,
}

if __name__ == "__main__":
    interactive_diagnostics()
