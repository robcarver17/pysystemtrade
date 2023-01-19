import datetime
from collections import namedtuple
from copy import copy

import numpy as np
import pandas as pd

from syscore.genutils import transfer_object_attributes
from syscore.pandas.pdutils import make_df_from_list_of_named_tuple
from sysproduction.data.broker import dataBroker
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.orders import dataOrders
from sysproduction.reporting.data.risk import (
    get_current_annualised_stdev_for_instrument,
)


def get_recent_broker_orders(data, start_date, end_date):
    data_orders = dataOrders(data)
    order_id_list = data_orders.get_historic_broker_order_ids_in_date_range(
        start_date, end_date
    )
    orders_as_list = [
        get_tuple_object_from_order_id(data, order_id) for order_id in order_id_list
    ]
    pdf = make_df_from_list_of_named_tuple(tradesData, orders_as_list)

    return pdf


def create_raw_slippage_df(broker_orders):
    raw_slippage_data_as_list = [
        raw_slippage_row(broker_orders.iloc[irow]) for irow in range(len(broker_orders))
    ]
    if len(raw_slippage_data_as_list) > 0:
        raw_slippage_df = pd.concat(raw_slippage_data_as_list, axis=1)
        raw_slippage_df = raw_slippage_df.transpose()
        raw_slippage_df.index = broker_orders.index
        result = raw_slippage_df
    else:
        result = pd.DataFrame(columns=NEW_ORDER_ROW_COLS + NEW_ORDER_ROW_INDEX_COLS)

    return result


def get_tuple_object_from_order_id(data, order_id):
    data_orders = dataOrders(data)
    order = data_orders.get_historic_broker_order_from_order_id_with_execution_data(
        order_id
    )
    tuple_object = transfer_object_attributes(tradesData, order)

    return tuple_object


terseTradesData = namedtuple(
    "terseTradesData",
    [
        "instrument_code",
        "strategy_name",
        "contract_date",
        "fill_datetime",
        "fill",
        "filled_price",
    ],
)


tradesData = namedtuple(
    "tradesData",
    [
        "order_id",
        "instrument_code",
        "strategy_name",
        "contract_date",
        "fill",
        "filled_price",
        "mid_price",
        "side_price",
        "offside_price",
        "parent_reference_price",  # from contract order
        "parent_reference_datetime",  # from instrument order
        "submit_datetime",
        "fill_datetime",
        "limit_price",
        "trade",
        "buy_or_sell",
        "parent_limit_price",
        "commission",
    ],
)

NEW_ORDER_ROW_COLS = [
    "instrument_code",
    "strategy_name",
    "trade",
    "parent_reference_price",
    "parent_limit_price",
    "mid_price",
    "side_price",
    "offside_price",
    "limit_price",
    "filled_price",
]
NEW_ORDER_ROW_INDEX_COLS = [
    "delay",
    "bid_ask",
    "execution",
    "versus_limit",
    "versus_parent_limit",
    "total_trading",
]


def raw_slippage_row(order_row):
    (
        delay,
        bid_ask,
        execution,
        versus_limit,
        versus_parent_limit,
        total_trading,
    ) = price_calculations_for_order_row(order_row)
    new_order_row = copy(order_row)
    new_order_row = new_order_row[NEW_ORDER_ROW_COLS]
    new_order_row = new_order_row.append(
        pd.Series(
            [
                delay,
                bid_ask,
                execution,
                versus_limit,
                versus_parent_limit,
                total_trading,
            ],
            index=NEW_ORDER_ROW_INDEX_COLS,
        )
    )

    return new_order_row


def price_calculations_for_order_row(order_row):
    buying_multiplier = order_row.buy_or_sell

    # Following are always floats: parent_reference_price, limit_price,
    # calculated_mid_price, calculated_side_price, fill_price
    delay = price_slippage(
        buying_multiplier,
        order_row.parent_reference_price,
        order_row.mid_price,
    )

    bid_ask = price_slippage(
        buying_multiplier,
        order_row.mid_price,
        order_row.side_price,
    )

    execution = price_slippage(
        buying_multiplier,
        order_row.side_price,
        order_row.filled_price,
    )

    total_trading = bid_ask + execution

    versus_limit = price_slippage(
        buying_multiplier, order_row.limit_price, order_row.filled_price
    )

    versus_parent_limit = price_slippage(
        buying_multiplier,
        order_row.parent_limit_price,
        order_row.filled_price,
    )

    return delay, bid_ask, execution, versus_limit, versus_parent_limit, total_trading


def price_slippage(buying_multiplier, first_price, second_price):
    # Slippage is always negative (bad) positive (good)
    # This will return a negative number if second price is adverse versus
    # first price
    if first_price is None or second_price is None:
        return np.nan

    # 1 if buying, -1 if selling
    # if buying, want second price to be lower than first
    # if selling, want second price to be higher than first
    slippage = buying_multiplier * (first_price - second_price)
    return slippage


def create_cash_slippage_df(raw_slippage, data):
    # What does this slippage mean in money terms

    cash_slippage_data_as_list = [
        cash_slippage_row(raw_slippage.iloc[irow], data)
        for irow in range(len(raw_slippage))
    ]
    cash_slippage_df = pd.concat(cash_slippage_data_as_list, axis=1)
    cash_slippage_df = cash_slippage_df.transpose()
    cash_slippage_df.index = raw_slippage.index

    return cash_slippage_df


def cash_slippage_row(slippage_row, data):
    # rewrite
    (
        delay_cash,
        bid_ask_cash,
        execution_cash,
        versus_limit_cash,
        versus_parent_limit_cash,
        total_trading_cash,
        value_of_price_point,
    ) = cash_calculations_for_slippage_row(slippage_row, data)
    new_slippage_row = copy(slippage_row)
    new_slippage_row = new_slippage_row[
        [
            "instrument_code",
            "strategy_name",
            "trade",
        ]
    ]
    new_slippage_row = new_slippage_row.append(
        pd.Series(
            [
                value_of_price_point,
                delay_cash,
                bid_ask_cash,
                execution_cash,
                versus_limit_cash,
                versus_parent_limit_cash,
                total_trading_cash,
            ],
            index=[
                "value_of_price_point",
                "delay_cash",
                "bid_ask_cash",
                "execution_cash",
                "versus_limit_cash",
                "versus_parent_limit_cash",
                "total_trading_cash",
            ],
        )
    )

    return new_slippage_row


def cash_calculations_for_slippage_row(slippage_row, data):
    # What's a tick worth in base currency?
    diag_instruments = diagInstruments(data)
    value_of_price_point = diag_instruments.get_point_size_base_currency(
        slippage_row.instrument_code
    )
    input_items = [
        "delay",
        "bid_ask",
        "execution",
        "versus_limit",
        "versus_parent_limit",
        "total_trading",
    ]
    output = [
        value_of_price_point * slippage_row[input_name] for input_name in input_items
    ]

    return tuple(output + [value_of_price_point])


def create_vol_norm_slippage_df(raw_slippage, data):
    # What does this slippage mean in vol normalised terms
    for irow in range(len(raw_slippage)):
        vol_slippage_row(raw_slippage.iloc[irow], data)

    vol_slippage_data_as_list = [
        vol_slippage_row(raw_slippage.iloc[irow], data)
        for irow in range(len(raw_slippage))
    ]
    vol_slippage_df = pd.concat(vol_slippage_data_as_list, axis=1)
    vol_slippage_df = vol_slippage_df.transpose()
    vol_slippage_df.index = raw_slippage.index

    return vol_slippage_df


def vol_slippage_row(slippage_row, data):
    # rewrite
    (
        vol_delay,
        vol_bid_ask,
        vol_execution,
        vol_versus_limit,
        vol_versus_parent_limit,
        total_trading_vol,
        last_annual_vol,
    ) = vol_calculations_for_slippage_row(slippage_row, data)
    new_slippage_row = copy(slippage_row)
    new_slippage_row = new_slippage_row[
        [
            "instrument_code",
            "strategy_name",
            "trade",
        ]
    ]
    new_slippage_row = new_slippage_row.append(
        pd.Series(
            [
                last_annual_vol,
                vol_delay,
                vol_bid_ask,
                vol_execution,
                vol_versus_limit,
                vol_versus_parent_limit,
                total_trading_vol,
            ],
            index=[
                "last_annual_vol",
                "delay_vol",
                "bid_ask_vol",
                "execution_vol",
                "versus_limit_vol",
                "versus_parent_limit_vol",
                "total_trading_vol",
            ],
        )
    )

    return new_slippage_row


def vol_calculations_for_slippage_row(slippage_row, data):

    last_annual_vol = get_last_annual_vol_for_slippage_row(slippage_row, data)

    input_items = [
        "delay",
        "bid_ask",
        "execution",
        "versus_limit",
        "versus_parent_limit",
        "total_trading",
    ]
    output = [
        10000 * slippage_row[input_name] / last_annual_vol for input_name in input_items
    ]

    return tuple(output + [last_annual_vol])


def get_last_annual_vol_for_slippage_row(slippage_row, data):
    instrument_code = slippage_row.instrument_code
    last_annual_vol = get_current_annualised_stdev_for_instrument(data, instrument_code)

    return last_annual_vol


def get_stats_for_slippage_groups(df_to_process, item_list):
    results = {}
    for item_name in item_list:

        sum_data = df_to_process.groupby(["strategy_name", "instrument_code"]).agg(
            {item_name: "sum"}
        )

        results[item_name + " Sum"] = sum_data

        total_sum_data = df_to_process.groupby(["strategy_name"]).agg(
            {item_name: "sum"}
        )

        results[item_name + " Total Sum"] = total_sum_data

    return results


def create_delay_df(broker_orders):
    delay_data_as_list = [
        delay_row(broker_orders.iloc[irow]) for irow in range(len(broker_orders))
    ]
    delay_data_df = pd.concat(delay_data_as_list, axis=1)
    delay_data_df = delay_data_df.transpose()
    delay_data_df.index = broker_orders.index

    return delay_data_df


def delay_row(order_row):
    submit_minus_generated, filled_minus_submit = delay_calculations_for_order_row(
        order_row
    )
    new_order_row = copy(order_row)
    new_order_row = new_order_row[
        [
            "instrument_code",
            "strategy_name",
            "parent_reference_datetime",
            "submit_datetime",
            "fill_datetime",
        ]
    ]
    new_order_row = new_order_row.append(
        pd.Series(
            [submit_minus_generated, filled_minus_submit],
            index=["submit_minus_generated", "filled_minus_submit"],
        )
    )

    return new_order_row


def delay_calculations_for_order_row(order_row):

    submit_minus_generated = delay_calc(
        order_row.parent_reference_datetime, order_row.submit_datetime
    )

    filled_minus_submit = delay_calc(order_row.submit_datetime, order_row.fill_datetime)

    return submit_minus_generated, filled_minus_submit


def delay_calc(first_time, second_time):
    if first_time is None or second_time is None:
        return np.nan

    time_diff = second_time - first_time
    time_diff_seconds = time_diff.total_seconds()

    if time_diff_seconds < 0:
        return np.nan

    return time_diff_seconds


def get_recent_trades_from_db_as_terse_df(data):
    data_orders = dataOrders(data)
    start_date = datetime.datetime.now() - datetime.timedelta(days=1)
    order_id_list = data_orders.get_historic_broker_order_ids_in_date_range(start_date)
    orders_as_list = [
        get_tuple_object_from_order_id(data, order_id) for order_id in order_id_list
    ]
    pdf = make_df_from_list_of_named_tuple(terseTradesData, orders_as_list)

    return pdf


def get_broker_trades_as_terse_df(data):
    data_broker = dataBroker(data)
    list_of_orders = data_broker.get_list_of_orders()
    tuple_list = [
        transfer_object_attributes(terseTradesData, order) for order in list_of_orders
    ]
    pdf = make_df_from_list_of_named_tuple(terseTradesData, tuple_list)

    return pdf
