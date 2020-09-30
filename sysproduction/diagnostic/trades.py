from copy import copy
from collections import  namedtuple

import datetime
import numpy as np
import pandas as pd

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

    overview = broker_orders[["instrument_code","strategy_name",  "contract_id","fill_datetime",
                                       "fill", "filled_price"]]

    delays = create_delay_df(broker_orders)
    raw_slippage = create_raw_slippage_df(broker_orders)

    results_object = dict(overview = overview, raw_slippage=raw_slippage)


    return results_object

def format_trades_data(results_object):
    """
    Put the results into a printable format

    :param results_dict: dict, keys are different segments
    :return:
    """


    formatted_output=[]

    formatted_output.append(header("Trades report produced on %s" % (str(datetime.datetime.now()))))

    table1_df = results_object['overview']
    table1 = table('Broker orders', table1_df)
    formatted_output.append(table1)


    return formatted_output


tradesData = namedtuple("tradesData", ["order_id", "instrument_code", "strategy_name",  "contract_id",
                                       "fill",
                                       "filled_price", "mid_price", "side_price",
                                       "parent_reference_price", # from contract order
                                        "parent_generated_datetime", # from instrument order
                                       "submit_datetime",
                                       "fill_datetime",
                                       "is_split_order",
                                       "calculated_filled_price",
                                       "calculated_mid_price",
                                       "calculated_side_price",
                                       "limit_price",
                                       "trade",
                                       "buy_or_sell",
                                       "parent_limit_price"
                                       ])

data = dataBlob()

def get_recent_broker_orders(data, start_date, end_date):
    data_orders = dataOrders(data)
    order_id_list = data_orders.get_historic_broker_orders_in_date_range(start_date, end_date)
    for order_id in order_id_list:
        get_tuple_object_from_order_id(data, order_id)
    orders_as_list = [get_tuple_object_from_order_id(data, order_id)
                      for order_id in order_id_list]
    pdf = make_df_from_list_of_named_tuple(tradesData, orders_as_list)

    return pdf


def get_tuple_object_from_order_id(data, order_id):
    data_orders = dataOrders(data)
    order = data_orders.get_historic_broker_order_from_order_id_with_execution_data(order_id)
    tuple_object = transfer_object_attributes(tradesData, order)

    return tuple_object

def create_delay_df(broker_orders):
    delay_data_as_list = [delay_row(broker_orders.iloc[irow])
                          for irow in range(len(broker_orders))]
    delay_data_df = pd.concat(delay_data_as_list, axis=1)
    delay_data_df = delay_data_df.transpose()
    delay_data_df.index = broker_orders.index

    return delay_data_df

def delay_row(order_row):
    submit_minus_generated, filled_minus_submit = delay_calculations_for_order_row(order_row)
    new_order_row = copy(order_row)
    new_order_row = new_order_row[['instrument_code', 'strategy_name', 'parent_generated_datetime',
                                   'submit_datetime', 'fill_datetime']]
    new_order_row = new_order_row.append(pd.Series([submit_minus_generated, filled_minus_submit],
                         index = ['submit_minus_generated', 'filled_minus_submit']))

    return new_order_row

def delay_calculations_for_order_row(order_row):

    submit_minus_generated = delay_calc(
                                        order_row.parent_generated_datetime,
                                        order_row.submit_datetime)

    filled_minus_submit = delay_calc(order_row.submit_datetime,
                                     order_row.fill_datetime)


    return submit_minus_generated, filled_minus_submit

def delay_calc(first_time, second_time):
    if first_time is None or second_time is None:
        return np.nan

    time_diff = second_time - first_time
    time_diff_seconds = time_diff.total_seconds()

    if time_diff_seconds<0:
        return np.nan

    return time_diff_seconds


def create_raw_slippage_df(broker_orders):
    raw_slippage_data_as_list = [raw_slippage_row(broker_orders.iloc[irow])
                          for irow in range(len(broker_orders))]
    raw_slippage_df = pd.concat(raw_slippage_data_as_list, axis=1)
    raw_slippage_df = raw_slippage_df.transpose()
    raw_slippage_df.index = broker_orders.index

    return raw_slippage_df

def raw_slippage_row(order_row):
    delay, bid_ask, execution, versus_limit, versus_parent_limit = price_calculations_for_order_row(order_row)
    new_order_row = copy(order_row)
    new_order_row = new_order_row[['instrument_code', 'strategy_name',
                                   "trade",
                                   'parent_reference_price',
                                   'parent_limit_price',
                                   'calculated_mid_price',
                                   'calculated_side_price',
                                   'limit_price',
                                   'calculated_filled_price']]
    new_order_row = new_order_row.append(pd.Series([delay, bid_ask, execution, versus_limit, versus_parent_limit],
                         index = ['delay', 'bid_ask', 'execution', 'versus_limit', 'versus_parent_limit']))

    return new_order_row


def price_calculations_for_order_row(order_row):
    buying_multiplier = order_row.buy_or_sell

    ## Following are always floats: parent_reference_price, limit_price, calculated_mid_price, calculated_side_price, fill_price
    delay = price_slippage(buying_multiplier, order_row.parent_reference_price,
                                   order_row.calculated_mid_price)

    bid_ask = price_slippage(buying_multiplier, order_row.calculated_mid_price,
                             order_row.calculated_side_price)

    execution = price_slippage(buying_multiplier, order_row.calculated_side_price,
                               order_row.calculated_filled_price)

    versus_limit = price_slippage(buying_multiplier, order_row.limit_price,
                                  order_row.calculated_filled_price)

    versus_parent_limit = price_slippage(buying_multiplier, order_row.parent_limit_price,
                                         order_row.calculated_filled_price)

    return delay, bid_ask, execution, versus_limit, versus_parent_limit

def price_slippage(buying_multiplier, first_price, second_price):
    ## Slippage is always negative (bad) positive (good)
    ## This will return a negative number if second price is adverse versus first price
    if first_price is None or second_price is None:
        return np.nan

    ## 1 if buying, -1 if selling
    ## if buying, want second price to be lower than first
    ## if selling, want second price to be higher than first
    slippage = buying_multiplier * (first_price - second_price)
    return slippage
