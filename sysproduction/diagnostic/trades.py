from copy import copy
from collections import namedtuple

import datetime
import numpy as np
import pandas as pd

from syscore.genutils import transfer_object_attributes
from syscore.pdutils import make_df_from_list_of_named_tuple
from syscore.objects import header, table, body_text, arg_not_supplied, missing_data

from sysdata.data_blob import dataBlob
from sysproduction.data.orders import dataOrders
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.prices import diagPrices

from sysproduction.diagnostic.risk import  get_current_annualised_stdev_for_instrument

def trades_info(
    data=arg_not_supplied,
    calendar_days_back=1,
    end_date=arg_not_supplied,
    start_date=arg_not_supplied,
):
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
        start_date = end_date - datetime.timedelta(days=calendar_days_back)

    results_object = get_trades_report_data(
        data, start_date=start_date, end_date=end_date
    )
    formatted_output = format_trades_data(results_object)

    return formatted_output


def get_trades_report_data(data, start_date, end_date):

    broker_orders = get_recent_broker_orders(data, start_date, end_date)
    if len(broker_orders) == 0:
        empty_df = pd.DataFrame()
        results_object = dict(overview=empty_df)
        return results_object

    overview = broker_orders[
        [
            "instrument_code",
            "strategy_name",
            "contract_id",
            "fill_datetime",
            "fill",
            "filled_price",
        ]
    ]

    delays = create_delay_df(broker_orders)
    raw_slippage = create_raw_slippage_df(broker_orders)
    vol_slippage = create_vol_norm_slippage_df(raw_slippage, data)
    cash_slippage = create_cash_slippage_df(raw_slippage, data)

    summary_dict = {}
    item_list = [
        "delay",
        "bid_ask",
        "execution",
        "versus_limit",
        "versus_parent_limit",
        "total_trading",
    ]
    detailed_raw_results = get_stats_for_slippage_groups(
        raw_slippage, item_list)
    summary_dict.update(detailed_raw_results)

    item_list = [
        "delay_vol",
        "bid_ask_vol",
        "execution_vol",
        "versus_limit_vol",
        "versus_parent_limit_vol",
        "total_trading_vol",
    ]
    detailed_vol_results = get_stats_for_slippage_groups(
        vol_slippage, item_list)
    summary_dict.update(detailed_vol_results)

    item_list = [
        "delay_cash",
        "bid_ask_cash",
        "execution_cash",
        "versus_limit_cash",
        "versus_parent_limit_cash",
        "total_trading_cash",
    ]
    detailed_cash_results = get_stats_for_slippage_groups(
        cash_slippage, item_list)
    summary_dict.update(detailed_cash_results)

    results_object = dict(
        overview=overview,
        delays=delays,
        raw_slippage=raw_slippage,
        vol_slippage=vol_slippage,
        cash_slippage=cash_slippage,
        summary_dict=summary_dict,
    )

    return results_object


def format_trades_data(results_object):
    """
    Put the results into a printable format

    :param results_dict: dict, keys are different segments
    :return:
    """

    formatted_output = []

    formatted_output.append(
        header("Trades report produced on %s" % (str(datetime.datetime.now())))
    )

    if len(results_object["overview"]) == 0:
        formatted_output.append(body_text("No trades in relevant period"))

        return formatted_output

    table1_df = results_object["overview"]
    table1 = table("Broker orders", table1_df)
    formatted_output.append(table1)

    table2_df = results_object["delays"]
    table2 = table("Delays", table2_df)
    formatted_output.append(table2)

    table3_df = results_object["raw_slippage"]
    table3 = table("Slippage (ticks per lot)", table3_df)
    formatted_output.append(table3)

    table4_df = results_object["vol_slippage"]
    table4 = table(
        "Slippage (normalised by annual vol, BP of annual SR)",
        table4_df)
    formatted_output.append(table4)

    table5_df = results_object["cash_slippage"]
    table5 = table("Slippage (In base currency)", table5_df)
    formatted_output.append(table5)

    summary_results_dict = results_object["summary_dict"]
    for summary_table_name, summary_table_item in summary_results_dict.items():
        summary_table = table(
            "Summary %s" %
            summary_table_name,
            summary_table_item)
        formatted_output.append(summary_table)

    return formatted_output


tradesData = namedtuple(
    "tradesData",
    [
        "order_id",
        "instrument_code",
        "strategy_name",
        "contract_id",
        "fill",
        "filled_price",
        "mid_price",
        "side_price",
        "parent_reference_price",  # from contract order
        "parent_generated_datetime",  # from instrument order
        "submit_datetime",
        "fill_datetime",
        "is_split_order",
        "calculated_filled_price",
        "calculated_mid_price",
        "calculated_side_price",
        "limit_price",
        "trade",
        "buy_or_sell",
        "parent_limit_price",
        "commission",
    ],
)

data = dataBlob()


def get_recent_broker_orders(data, start_date, end_date):
    data_orders = dataOrders(data)
    order_id_list = data_orders.get_historic_broker_orders_in_date_range(
        start_date, end_date
    )
    orders_as_list = [get_tuple_object_from_order_id(
        data, order_id) for order_id in order_id_list]
    pdf = make_df_from_list_of_named_tuple(tradesData, orders_as_list)

    return pdf


def get_tuple_object_from_order_id(data, order_id):
    data_orders = dataOrders(data)
    order = data_orders.get_historic_broker_order_from_order_id_with_execution_data(
        order_id)
    tuple_object = transfer_object_attributes(tradesData, order)

    return tuple_object


def create_delay_df(broker_orders):
    delay_data_as_list = [
        delay_row(
            broker_orders.iloc[irow]) for irow in range(
            len(broker_orders))]
    delay_data_df = pd.concat(delay_data_as_list, axis=1)
    delay_data_df = delay_data_df.transpose()
    delay_data_df.index = broker_orders.index

    return delay_data_df


def delay_row(order_row):
    submit_minus_generated, filled_minus_submit = delay_calculations_for_order_row(
        order_row)
    new_order_row = copy(order_row)
    new_order_row = new_order_row[
        [
            "instrument_code",
            "strategy_name",
            "parent_generated_datetime",
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
        order_row.parent_generated_datetime, order_row.submit_datetime
    )

    filled_minus_submit = delay_calc(
        order_row.submit_datetime,
        order_row.fill_datetime)

    return submit_minus_generated, filled_minus_submit


def delay_calc(first_time, second_time):
    if first_time is None or second_time is None:
        return np.nan

    time_diff = second_time - first_time
    time_diff_seconds = time_diff.total_seconds()

    if time_diff_seconds < 0:
        return np.nan

    return time_diff_seconds


def create_raw_slippage_df(broker_orders):
    raw_slippage_data_as_list = [
        raw_slippage_row(
            broker_orders.iloc[irow]) for irow in range(
            len(broker_orders))]
    raw_slippage_df = pd.concat(raw_slippage_data_as_list, axis=1)
    raw_slippage_df = raw_slippage_df.transpose()
    raw_slippage_df.index = broker_orders.index

    return raw_slippage_df


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
    new_order_row = new_order_row[
        [
            "instrument_code",
            "strategy_name",
            "trade",
            "parent_reference_price",
            "parent_limit_price",
            "calculated_mid_price",
            "calculated_side_price",
            "limit_price",
            "calculated_filled_price",
        ]
    ]
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
            index=[
                "delay",
                "bid_ask",
                "execution",
                "versus_limit",
                "versus_parent_limit",
                "total_trading",
            ],
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
        order_row.calculated_mid_price,
    )

    bid_ask = price_slippage(
        buying_multiplier,
        order_row.calculated_mid_price,
        order_row.calculated_side_price,
    )

    execution = price_slippage(
        buying_multiplier,
        order_row.calculated_side_price,
        order_row.calculated_filled_price,
    )

    total_trading = bid_ask + execution

    versus_limit = price_slippage(
        buying_multiplier,
        order_row.limit_price,
        order_row.calculated_filled_price)

    versus_parent_limit = price_slippage(
        buying_multiplier,
        order_row.parent_limit_price,
        order_row.calculated_filled_price,
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
    output = [value_of_price_point * slippage_row[input_name]
              for input_name in input_items]

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
    output = [10000 * slippage_row[input_name] /
              last_annual_vol for input_name in input_items]

    return tuple(output + [last_annual_vol])


def get_last_annual_vol_for_slippage_row(slippage_row, data):
    instrument_code = slippage_row.instrument_code
    last_annual_vol = get_current_annualised_stdev_for_instrument(data,
        instrument_code)

    return last_annual_vol


def get_stats_for_slippage_groups(df_to_process, item_list):
    results = {}
    for item_name in item_list:

        sum_data = df_to_process.groupby(
            ["strategy_name", "instrument_code"]).agg({item_name: "sum"})
        count_data = df_to_process.groupby(
            ["strategy_name", "instrument_code"]).agg({item_name: "count"})
        avg_data = sum_data / count_data

        try:
            std = df_to_process.groupby(
                ["strategy_name", "instrument_code"]).agg({item_name: "std"})
        except pd.core.base.DataError:
            # not enough items to calculate standard deviation
            std = np.nan

        lower_range = avg_data + (-2 * std)
        upper_range = avg_data + (2 * std)

        results[item_name + " Sum"] = sum_data
        results[item_name + " Count"] = count_data
        results[item_name + " Mean"] = avg_data
        results[item_name + " Lower range"] = lower_range
        results[item_name + " Upper range"] = upper_range

        total_sum_data = df_to_process.groupby(["strategy_name"]).agg(
            {item_name: "sum"}
        )

        results[item_name + " Total Sum"] = total_sum_data

    return results
