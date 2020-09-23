
from collections import  namedtuple

import datetime

from syscore.genutils import transfer_object_attributes
from syscore.pdutils import make_df_from_list_of_named_tuple
from syscore.objects import header, table, body_text, arg_not_supplied, missing_data

from sysproduction.data.get_data import dataBlob
from sysproduction.data.orders import dataOrders

def trades_info(data =arg_not_supplied, calendar_days_back = 1, end_date = arg_not_supplied,
                start_date = arg_not_supplied):
    """
    Report on system status

    :param: data blob
    :return: list of formatted output items
    """
    if data is arg_not_supplied:
        data = dataBlob()

    if end_date is arg_not_supplied:
        end_date = datetime.datetime.now()

    if start_date is arg_not_supplied:
        start_date = end_date - datetime.timedelta(days = calendar_days_back)

    results_object = get_trades_report_data(data, start_date = start_date, end_date = end_date)
    formatted_output = format_trades_data(results_object)

    return formatted_output

def get_trades_report_data(data, start_date, end_date):

    broker_orders = get_recent_broker_orders(data, start_date, end_date)
    results_object = dict(broker_orders = broker_orders)

    return results_object

def format_trades_data(results_object):
    """
    Put the results into a printable format

    :param results_dict: dict, keys are different segments
    :return:
    """


    formatted_output=[]

    formatted_output.append(header("Trades report produced on %s" % (str(datetime.datetime.now()))))

    table1_df = results_object['broker_orders']
    table1 = table('Broker orders', table1_df)
    formatted_output.append(table1)


    return formatted_output


tradesData = namedtuple("tradesData", ["instrument_code","strategy_name",  "contract_id","fill_datetime",
                                       "fill", "filled_price"])


data = dataBlob()

def get_recent_broker_orders(data, start_date, end_date):
    data_orders = dataOrders(data)
    order_id_list = data_orders.get_historic_broker_orders_in_date_range(start_date, end_date)
    orders_as_list = [get_tuple_object_from_order_id(data, order_id)
                      for order_id in order_id_list]
    pdf = make_df_from_list_of_named_tuple(tradesData, orders_as_list)

    return pdf


def get_tuple_object_from_order_id(data, order_id):
    data_orders = dataOrders(data)
    order = data_orders.get_historic_broker_order_from_order_id(order_id)
    tuple_object = transfer_object_attributes(tradesData, order)

    return tuple_object
