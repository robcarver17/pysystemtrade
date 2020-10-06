import datetime
import pandas as pd
import numpy as np
import types

from collections import namedtuple

from syscore.objects import header, table, body_text, arg_not_supplied, missing_data
from sysproduction.data.capital import dataCapital

from sysproduction.data.currency_data import currencyData
from sysproduction.data.prices import diagPrices
from sysproduction.data.orders import dataOrders
from sysproduction.data.positions import diagPositions
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.strategies import diagStrategiesConfig

# We want a p&l (We could merge this into another kind of report)
# We want to be able to have it emailed, or run it offline
# To have it emailed, we'll call the report function and optionally pass the output to a text file not stdout
# Reports consist of multiple calls to functions with data object, each of which returns a displayable object
# We also chuck in a title and a timestamp


def pandl_info(
        data,
        calendar_days_back=7,
        start_date=arg_not_supplied,
        end_date=arg_not_supplied):
    """

    To begin with we calculate::

    - change in total p&l from total capital
    - p&l for each instrument, by summing over p&l per contract

    :param: data blob
    :return: list of formatted output items
    """
    if end_date is arg_not_supplied:
        end_date = datetime.datetime.now()
    if start_date is arg_not_supplied:
        start_date = datetime.datetime.now() - datetime.timedelta(
            days=calendar_days_back
        )

    results_object = get_pandl_report_data(
        data, start_date=start_date, end_date=end_date
    )
    formatted_output = format_pandl_data(results_object)

    return formatted_output


pandlResults = namedtuple(
    "pandlResults",
    [
        "total_capital_pandl",
        "start_date",
        "end_date",
        "pandl_for_instruments_across_strategies",
        "futures_total",
        "residual",
        "strategies",
        "sector_pandl",
    ],
)


def get_pandl_report_data(data, start_date, end_date):
    """

    :param data: data Blob
    :param calendar_days_back:
    :return: named tuple object containing p&l data
    """
    # to save double calculation
    data.temp_pandl_read = types.MethodType(temp_pandl_read, data)
    data.temp_pandl_write = types.MethodType(temp_pandl_write, data)

    total_capital_pandl = (
        get_total_capital_pandl(data, start_date, end_date=end_date) * 100
    )
    pandl_for_instruments_across_strategies = (
        get_ranked_list_of_pandl_by_instrument_all_strategies_in_date_range(
            data, start_date, end_date
        )
    )
    pandl_for_instruments_across_strategies.pandl = (
        pandl_for_instruments_across_strategies.pandl * 100
    )
    total_for_futures = pandl_for_instruments_across_strategies.pandl.sum()
    residual = total_capital_pandl - total_for_futures
    strategies = get_strategy_pandl_and_residual(data, start_date, end_date)
    sector_pandl = get_sector_pandl(data, start_date, end_date)

    results_object = pandlResults(
        total_capital_pandl,
        start_date,
        end_date,
        pandl_for_instruments_across_strategies,
        total_for_futures,
        residual,
        strategies,
        sector_pandl,
    )

    return results_object


def temp_pandl_write(self, instrument_code, pandl_data):
    meta_data = getattr(self, "meta_data", None)
    if meta_data is None:
        self.meta_data = {}
    self.meta_data[instrument_code] = pandl_data


def temp_pandl_read(self, instrument_code):
    meta_data = getattr(self, "meta_data", None)
    if meta_data is None:
        return None
    data = meta_data.get(instrument_code, None)
    return data


def get_total_capital_series(data):
    data_capital_object = dataCapital(data)

    return data_capital_object.get_series_of_maximum_capital()


def get_strategy_capital_series(data, strategy_name):
    data_capital_object = dataCapital(data)

    return data_capital_object.get_capital_pd_series_for_strategy(
        strategy_name)


def get_daily_perc_pandl(data):
    data_capital_object = dataCapital(data)

    # This is for 'non compounding' p&l
    total_pandl_series = data_capital_object.get_series_of_accumulated_capital()
    daily_pandl_series = total_pandl_series.ffill().diff()

    all_capital = get_total_capital_series(data)

    perc_pandl_series = daily_pandl_series / all_capital

    return perc_pandl_series


def get_total_capital_pandl(data, start_date, end_date=arg_not_supplied):

    if end_date is arg_not_supplied:
        end_date = datetime.datetime.now()
    perc_pandl_series = get_daily_perc_pandl(data)

    relevant_pandl = perc_pandl_series[start_date:end_date]
    pandl_in_period = relevant_pandl.sum()

    return pandl_in_period


def get_strategy_pandl_and_residual(data, start_date, end_date):
    strategies_pandl = get_ranked_list_of_pandl_by_strategy_in_date_range(
        data, start_date, end_date
    )
    total_pandl_strategies = strategies_pandl.pandl.sum()
    total_pandl = get_total_capital_pandl(data, start_date, end_date)
    residual_pandl = total_pandl - total_pandl_strategies
    residual_dfrow = pd.DataFrame(
        dict(codes=["residual"], pandl=residual_pandl))
    strategies_pandl = strategies_pandl.append(residual_dfrow)
    strategies_pandl.pandl = strategies_pandl.pandl * 100

    return strategies_pandl


def get_ranked_list_of_pandl_by_instrument_all_strategies_in_date_range(
    data, start_date, end_date
):
    list_pandl = get_period_perc_pandl_for_all_instruments_all_strategies_in_date_range(
        data, start_date, end_date)
    list_pandl = [pandl for pandl in list_pandl if pandl.pandl != 0]
    list_pandl.sort(key=lambda r: r.pandl)

    pandl_as_df = list_pandl_to_df(list_pandl)

    return pandl_as_df


def get_sector_pandl(data, start_date, end_date):
    list_pandl = get_period_perc_pandl_for_all_sectors_in_date_range(
        data, start_date, end_date
    )
    list_pandl = [pandl for pandl in list_pandl if pandl.pandl != 0]
    list_pandl.sort(key=lambda r: r.pandl)

    pandl_as_df = list_pandl_to_df(list_pandl)

    return pandl_as_df


def get_ranked_list_of_pandl_by_strategy_in_date_range(
        data, start_date, end_date):
    list_pandl = get_period_perc_pandl_for_all_strategies_in_date_range(
        data, start_date, end_date
    )
    list_pandl.sort(key=lambda r: r.pandl)

    pandl_as_df = list_pandl_to_df(list_pandl)

    return pandl_as_df


PandL = namedtuple("PandL", ["code", "pandl"])


def list_pandl_to_df(list_pandl):
    code_list = [pandl.code for pandl in list_pandl]
    pandl_list = [pandl.pandl for pandl in list_pandl]

    return pd.DataFrame(dict(codes=code_list, pandl=pandl_list))


def get_period_perc_pandl_for_all_instruments_all_strategies_in_date_range(
    data, start_date, end_date
):
    diag_positions = diagPositions(data)
    instrument_list = diag_positions.get_list_of_instruments_with_any_position()

    list_pandl = [
        PandL(
            instrument_code,
            get_period_perc_pandl_for_instrument_all_strategies_in_date_range(
                data, instrument_code, start_date, end_date
            ),
        )
        for instrument_code in instrument_list
    ]

    return list_pandl


def get_period_perc_pandl_for_all_sectors_in_date_range(
        data, start_date, end_date):
    diag_instruments = diagInstruments(data)
    asset_classes = diag_instruments.get_all_asset_classes()
    list_pandl = [
        PandL(
            asset_class,
            get_period_perc_pandl_for_sector_in_date_range(
                asset_class, data, start_date, end_date
            ),
        )
        for asset_class in asset_classes
    ]

    return list_pandl


def get_period_perc_pandl_for_all_strategies_in_date_range(
        data, start_date, end_date):
    strategy_list = get_list_of_strategies(data)
    list_pandl = [
        PandL(
            strategy_name,
            get_period_perc_pandl_for_strategy_in_date_range(
                data, strategy_name, start_date, end_date
            ),
        )
        for strategy_name in strategy_list
    ]

    return list_pandl


def get_period_perc_pandl_for_sector_in_date_range(
    asset_class, data, start_date, end_date
):
    print("Getting data for %s" % asset_class)
    diag_instruments = diagInstruments(data)
    list_of_instruments = diag_instruments.get_all_instruments_in_asset_class(
        asset_class
    )
    instrument_pandl = [
        get_period_perc_pandl_for_instrument_all_strategies_in_date_range(
            data, instrument_code, start_date, end_date
        )
        for instrument_code in list_of_instruments
    ]
    asset_class_pandl = sum(instrument_pandl)

    return asset_class_pandl * 100


def get_period_perc_pandl_for_instrument_all_strategies_in_date_range(
    data, instrument_code, start_date, end_date
):
    print("Getting p&l for %s" % instrument_code)

    pandl_series = data.temp_pandl_read(instrument_code)
    if pandl_series is None:
        pandl_df = get_df_of_perc_pandl_series_for_instrument_all_strategies_across_contracts_in_date_range(
            data, instrument_code, start_date, end_date)

        if pandl_df is missing_data:
            return 0.0

        pandl_series = pandl_df.sum(axis=1)
        pandl_series = pandl_series[start_date:end_date]

        data.temp_pandl_write(instrument_code, pandl_series)

    return pandl_series.sum()


def get_period_perc_pandl_for_strategy_in_date_range(
    data, strategy_name, start_date, end_date
):
    print("Getting p&l for %s" % strategy_name)
    pandl_df = get_df_of_perc_pandl_series_for_strategy_all_instruments(
        data, strategy_name
    )

    if pandl_df is missing_data:
        return 0.0

    pandl_df = pandl_df[start_date:end_date]
    pandl_series = pandl_df.sum(axis=1, skipna=True)
    pandl_series = pandl_series.dropna()

    return pandl_series.sum()


def get_df_of_perc_pandl_series_for_instrument_all_strategies_across_contracts_in_date_range(
        data, instrument_code, start_date, end_date):
    (
        contract_list,
        pandl_list,
    ) = get_list_of_perc_pandl_series_for_instrument_all_strategies_across_contracts_in_date_range(
        data, instrument_code, start_date, end_date
    )

    if contract_list is missing_data:
        return missing_data

    pandl_df = pd.concat(pandl_list, axis=1)
    pandl_df.columns = contract_list

    return pandl_df


def get_df_of_perc_pandl_series_for_strategy_all_instruments(
        data,
        strategy_name):
    (instrument_list,
     pandl_list,
     ) = get_list_of_perc_pandl_series_for_strategy_all_instruments(data,
                                                                    strategy_name)

    if instrument_list is missing_data:
        return missing_data

    pandl_df = pd.concat(pandl_list, axis=1)
    pandl_df.columns = instrument_list

    return pandl_df


def get_list_of_perc_pandl_series_for_instrument_all_strategies_across_contracts_in_date_range(
        data, instrument_code, start_date, end_date):
    contract_list = get_list_of_contracts_held_for_an_instrument_in_date_range(
        data, instrument_code, start_date, end_date
    )
    if len(contract_list) == 0:
        return missing_data, missing_data

    pandl_list = [
        get_perc_pandl_series_for_contract(data, instrument_code, contract_id)
        for contract_id in contract_list
    ]

    return contract_list, pandl_list


def get_list_of_perc_pandl_series_for_strategy_all_instruments(
        data,
        strategy_name):
    instrument_list = get_list_of_instruments_held_for_a_strategy(
        data, strategy_name)
    if len(instrument_list) == 0:
        return missing_data, missing_data

    pandl_list = [
        get_perc_pandl_series_for_strategy_vs_total_capital(
            data, strategy_name, instrument_code
        )
        for instrument_code in instrument_list
    ]

    return instrument_list, pandl_list


def get_list_of_contracts_held_for_an_instrument_in_date_range(
    data, instrument_code, start_date, end_date
):
    diag_positions = diagPositions(data)

    contract_list = diag_positions.get_list_of_contracts_with_any_contract_position_for_instrument_in_date_range(
        instrument_code, start_date, end_date)

    return contract_list


def get_list_of_instruments_held_for_a_strategy(data, strategy_name):
    diag_positions = diagPositions(data)
    instrument_list = diag_positions.get_list_of_instruments_for_strategy_with_position(
        strategy_name)

    return instrument_list


def get_perc_pandl_series_for_contract(data, instrument_code, contract_id):
    pandl_in_base = get_pandl_series_in_base_ccy_for_contract(
        data, instrument_code, contract_id
    )
    capital = get_total_capital_series(data)
    capital = capital.reindex(pandl_in_base.index, method="ffill")

    perc_pandl = pandl_in_base / capital

    return perc_pandl


def get_perc_pandl_series_for_strategy_vs_total_capital(
    data, strategy_name, instrument_code
):
    print("Data for %s %s" % (strategy_name, instrument_code))
    pandl_in_base = get_pandl_series_in_base_ccy_for_strategy_instrument(
        data, strategy_name, instrument_code
    )
    capital = get_total_capital_series(data).ffill()
    capital = capital.reindex(pandl_in_base.index, method="ffill")

    perc_pandl = pandl_in_base / capital

    return perc_pandl


def get_pandl_series_in_base_ccy_for_contract(
        data, instrument_code, contract_id):
    pandl_in_local = get_pandl_series_in_local_ccy_for_contract(
        data, instrument_code, contract_id
    )
    fx_series = get_fx_series_for_instrument(data, instrument_code)
    fx_series = fx_series.reindex(pandl_in_local.index).ffill()

    pandl_in_base = fx_series * pandl_in_local

    return pandl_in_base


def get_pandl_series_in_base_ccy_for_strategy_instrument(
    data, strategy_name, instrument_code
):
    pandl_in_local = get_pandl_series_in_local_ccy_for_strategy_instrument(
        data, strategy_name, instrument_code
    )
    fx_series = get_fx_series_for_instrument(data, instrument_code)
    fx_series = fx_series.reindex(pandl_in_local.index).ffill()

    pandl_in_base = fx_series * pandl_in_local

    return pandl_in_base


def get_fx_series_for_instrument(data, instrument_code):
    diag_instruments = diagInstruments(data)
    currency = diag_instruments.get_currency(instrument_code)
    currency_data = currencyData(data)
    fx_series = currency_data.get_fx_prices_to_base(currency)

    return fx_series


def get_pandl_series_in_local_ccy_for_contract(
        data, instrument_code, contract_id):
    diag_instruments = diagInstruments(data)

    pandl_in_points = get_pandl_series_in_points_for_contract(
        data, instrument_code, contract_id
    )
    point_size = diag_instruments.get_point_size(instrument_code)
    pandl_in_local = point_size * pandl_in_points

    return pandl_in_local


def get_pandl_series_in_local_ccy_for_strategy_instrument(
    data, strategy_name, instrument_code
):
    diag_instruments = diagInstruments(data)

    pandl_in_points = get_pandl_series_in_points_for_instrument_strategy(
        data, instrument_code, strategy_name
    )
    point_size = diag_instruments.get_point_size(instrument_code)
    pandl_in_local = point_size * pandl_in_points

    return pandl_in_local


def get_pandl_series_in_points_for_contract(
        data, instrument_code, contract_id):
    pos_series = get_position_series_for_contract(
        data, instrument_code, contract_id)
    price_series = get_price_series_for_contract(
        data, instrument_code, contract_id)
    trade_df = get_trade_df_for_contract(data, instrument_code, contract_id)

    trade_df = unique_trades_df(trade_df)

    returns = pandl_points(price_series, trade_df, pos_series)

    return returns


def get_pandl_series_in_points_for_instrument_strategy(
    data, instrument_code, strategy_name
):
    pos_series = get_position_series_for_instrument_strategy(
        data, instrument_code, strategy_name
    )
    price_series = get_price_series_for_instrument(data, instrument_code)
    trade_df = get_trade_df_for_instrument(
        data, instrument_code, strategy_name)

    trade_df = unique_trades_df(trade_df)

    returns = pandl_points(price_series, trade_df, pos_series)

    return returns


def unique_trades_df(trade_df):
    cash_flow = trade_df.qty * trade_df.price
    trade_df["cash_flow"] = cash_flow
    new_df = trade_df.groupby(trade_df.index).sum()
    # qty and cash_flow will be correct, price won't be
    new_price = new_df.cash_flow / new_df.qty
    new_df["price"] = new_price
    new_df = new_df.drop("cash_flow", axis=1)

    return new_df


def pandl_points(price_series, trade_df, pos_series):
    """
    Calculate pandl for an individual position


    :param price: price series
    :type price: Tx1 pd.Series

    :param trade_series: set of trades done  NOT always aligned to price can be length 0
    :type trade_series: Tx2 pd.DataFrame columns ['qty', 'price']

    :param pos_series: series of positions NOT ALWAYS aligned to price
    :type pos_series: Tx1 pd.Series

    :returns: pd.Series

    """

    # want to have both kinds of price
    prices_to_use = pd.concat(
        [price_series, trade_df.price], axis=1, join="outer")

    # Where no fill price available, use price
    prices_to_use = prices_to_use.fillna(axis=1, method="ffill")

    prices_to_use = prices_to_use.price

    prices_to_use = prices_to_use.replace([np.inf, -np.inf], np.nan)
    prices_to_use = prices_to_use.dropna()

    price_returns = prices_to_use.ffill().diff()
    pos_series = pos_series.groupby(pos_series.index).last()
    pos_series = pos_series.reindex(price_returns.index, method="ffill")

    returns = pos_series.shift(1) * price_returns

    return returns


def get_price_series_for_contract(data, instrument_code, contract_id):
    diag_prices = diagPrices(data)
    all_prices = diag_prices.get_prices_for_instrument_code_and_contract_date(
        instrument_code, contract_id
    )
    price_series = all_prices.return_final_prices()

    return price_series


def get_price_series_for_instrument(data, instrument_code):
    diag_prices = diagPrices(data)
    price_series = diag_prices.get_prices_for_instrument(instrument_code)

    return price_series


def get_position_series_for_instrument_strategy(
        data, instrument_code, strategy_name):
    diag_positions = diagPositions(data)
    pos_series = diag_positions.get_position_df_for_strategy_and_instrument(
        strategy_name, instrument_code
    )
    if pos_series is missing_data:
        return pd.Series()

    return pd.Series(pos_series.position)


def get_trade_df_for_contract(data, instrument_code, contract_id):
    data_orders = dataOrders(data)
    list_of_trades = data_orders.get_fills_history_for_instrument_and_contract_id(
        instrument_code, contract_id)
    list_of_trades_as_pd_df = list_of_trades.as_pd_df()

    return list_of_trades_as_pd_df


def get_trade_df_for_instrument(data, instrument_code, strategy_name):
    data_orders = dataOrders(data)
    list_of_trades = data_orders.get_fills_history_for_strategy_and_instrument(
        strategy_name, instrument_code
    )
    list_of_trades_as_pd_df = list_of_trades.as_pd_df()

    return list_of_trades_as_pd_df


def get_position_series_for_contract(data, instrument_code, contract_id):
    diag_positions = diagPositions(data)
    pos_series = diag_positions.get_position_df_for_instrument_and_contract_id(
        instrument_code, contract_id
    )
    if pos_series is missing_data:
        return pd.Series()

    return pd.Series(pos_series.position)


def format_pandl_data(results_object):
    """
    Put the results into a printable format

    :param results_dict: dict, keys are instruments, contains roll information
    :return:
    """

    formatted_output = []

    formatted_output.append(
        header(
            "P&L report produced on %s from %s to %s"
            % (
                str(datetime.datetime.now()),
                str(results_object.start_date),
                str(results_object.end_date),
            )
        )
    )

    formatted_output.append(
        body_text("Total p&l is %.3f%%" % results_object.total_capital_pandl)
    )

    table1_df = results_object.pandl_for_instruments_across_strategies

    table1_df = table1_df.round(2)

    table1 = table("P&L by instrument for all strategies", table1_df)

    formatted_output.append(table1)

    formatted_output.append(
        body_text("Total futures p&l is %.3f%%" % results_object.futures_total)
    )

    formatted_output.append(
        body_text("Residual p&l is %.3f%%" % results_object.residual)
    )

    table2_df = results_object.strategies

    table2_df = table2_df.round(2)

    table2 = table("P&L by strategy", table2_df)

    formatted_output.append(table2)

    table3_df = results_object.sector_pandl
    table3_df = table3_df.round(2)
    table3 = table("P&L by asset class", table3_df)

    formatted_output.append(table3)

    formatted_output.append(header("END OF P&L REPORT"))

    return formatted_output


def get_list_of_strategies(data):
    diag_positions = diagPositions(data)
    return diag_positions.get_list_of_strategies_with_positions()
