"""
Monitor health of system by seeing when things last run

We can also check: when last adjusted prices were updated, when FX was last updated, when optimal position was
   last updated
"""
from collections import namedtuple

import datetime

from syscore.genutils import transfer_object_attributes
from syscore.pdutils import make_df_from_list_of_named_tuple
from syscore.objects import header, table, body_text, arg_not_supplied, missing_data

from sysproduction.data.get_data import dataBlob
from sysproduction.data.orders import dataOrders
from sysproduction.data.positions import diagPositions
from sysproduction.data.broker import dataBroker
from sysproduction.data.positions import dataOptimalPositions


def reconcile_info(data=arg_not_supplied):
    """
    Report on system status

    :param: data blob
    :return: list of formatted output items
    """
    if data is arg_not_supplied:
        data = dataBlob()

    results_object = get_reconcile_report_data(data)
    formatted_output = format_reconcile_data(results_object)

    return formatted_output


def get_reconcile_report_data(data):

    positions_optimal = get_optimal_positions(data)
    positions_mine = get_my_positions(data)
    positions_ib = get_broker_positions(data)
    position_breaks = get_position_breaks(data)
    trades_mine = get_recent_trades_from_db(data)
    trades_ib = get_broker_trades(data)

    results_object = dict(
        positions_mine=positions_mine,
        positions_ib=positions_ib,
        position_breaks=position_breaks,
        trades_mine=trades_mine,
        trades_ib=trades_ib,
        positions_optimal=positions_optimal,
    )
    return results_object


def format_reconcile_data(results_object):
    """
    Put the results into a printable format

    :param results_dict: dict, keys are different segments
    :return:
    """

    formatted_output = []

    formatted_output.append(
        header(
            "Reconcile report produced on %s" %
            (str(
                datetime.datetime.now()))))

    table0_df = results_object["positions_optimal"]
    table0 = table("Optimal versus actual positions", table0_df)
    formatted_output.append(table0)

    table1_df = results_object["positions_mine"]
    table1 = table("Positions in DB", table1_df)
    formatted_output.append(table1)

    table2_df = results_object["positions_ib"]
    table2 = table("Positions broker", table2_df)
    formatted_output.append(table2)

    text1 = body_text(results_object["position_breaks"])
    formatted_output.append(text1)

    table3_df = results_object["trades_mine"]
    table3 = table("Trades in DB", table3_df)
    formatted_output.append(table3)

    table4_df = results_object["trades_ib"]
    table4 = table("Trades from broker", table4_df)
    formatted_output.append(table4)

    formatted_output.append(header("END OF STATUS REPORT"))

    return formatted_output


def get_optimal_positions(data):
    data_optimal = dataOptimalPositions(data)
    opt_positions = data_optimal.get_pd_of_position_breaks()

    return opt_positions


def get_my_positions(data):
    data_broker = dataBroker(data)
    my_positions = data_broker.get_db_contract_positions_with_IB_expiries().as_pd_df()
    my_positions = my_positions.sort_values("instrument_code")

    return my_positions


def get_broker_positions(data):
    data_broker = dataBroker(data)
    broker_positions = data_broker.get_all_current_contract_positions().as_pd_df()
    broker_positions = broker_positions.sort_values("instrument_code")
    return broker_positions


def get_position_breaks(data):

    data_optimal = dataOptimalPositions(data)
    breaks_str0 = "Breaks Optimal vs actual %s" % str(
        data_optimal.get_list_of_optimal_position_breaks()
    )

    diag_positions = diagPositions(data)
    breaks_str1 = "Breaks Instrument vs Contract %s" % str(
        diag_positions.get_list_of_breaks_between_contract_and_strategy_positions())

    data_broker = dataBroker(data)
    breaks_str2 = "Breaks Broker vs Contract %s" % str(
        data_broker.get_list_of_breaks_between_broker_and_db_contract_positions())

    return breaks_str0 + "\n " + breaks_str1 + "\n " + breaks_str2


tradesData = namedtuple(
    "tradesData",
    [
        "instrument_code",
        "strategy_name",
        "contract_id",
        "fill_datetime",
        "fill",
        "filled_price",
    ],
)


def get_recent_trades_from_db(data):
    data_orders = dataOrders(data)
    start_date = datetime.datetime.now() - datetime.timedelta(days=1)
    order_id_list = data_orders.get_historic_broker_orders_in_date_range(
        start_date)
    orders_as_list = [get_tuple_object_from_order_id(
        data, order_id) for order_id in order_id_list]
    pdf = make_df_from_list_of_named_tuple(tradesData, orders_as_list)

    return pdf


def get_tuple_object_from_order_id(data, order_id):
    data_orders = dataOrders(data)
    order = data_orders.get_historic_broker_order_from_order_id(order_id)
    tuple_object = transfer_object_attributes(tradesData, order)

    return tuple_object


def get_broker_trades(data):
    data_broker = dataBroker(data)
    list_of_orders = data_broker.get_list_of_orders()
    tuple_list = [
        transfer_object_attributes(
            tradesData,
            order) for order in list_of_orders]
    pdf = make_df_from_list_of_named_tuple(tradesData, tuple_list)

    return pdf
