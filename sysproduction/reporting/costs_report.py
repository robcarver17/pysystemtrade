## Generate expected spread from actual trades, and sampled spreads
import datetime
import pandas as pd
from sysdata.data_blob import dataBlob

from syscore.dateutils import n_days_ago

from sysproduction.data.prices import diagPrices
from sysproduction.data.instruments import diagInstruments
from sysproduction.reporting.trades_report import create_raw_slippage_df, get_recent_broker_orders

from syscore.objects import header, table, body_text, arg_not_supplied, missing_data

def costs_report(
    data: dataBlob=arg_not_supplied,
    calendar_days_back: int = 250,
    end_date: datetime.datetime = arg_not_supplied,
    start_date: datetime.datetime = arg_not_supplied):

    if data is arg_not_supplied:
        data = dataBlob()

    if end_date is arg_not_supplied:
        end_date = datetime.datetime.now()

    if start_date is arg_not_supplied:
        start_date = n_days_ago(calendar_days_back, date_ref=end_date)

    costs_report_data = get_costs_report_data(
        data, start_date=start_date, end_date=end_date
    )
    formatted_output = format_costs_data(costs_report_data)

    return formatted_output

def get_costs_report_data(data: dataBlob,
                             start_date: datetime.datetime,
                             end_date: datetime.datetime) -> dict:
    combined_df_costs = get_combined_df_of_costs(data,
                                                 start_date=start_date,
                                                 end_date=end_date)
    combined_df_costs = combined_df_costs.round(6)


    costs_report_data = dict(combined_df_costs = combined_df_costs,
                             start_date = start_date,
                             end_date = end_date)

    return costs_report_data


def get_combined_df_of_costs(data: dataBlob,
                             start_date: datetime.datetime,
                             end_date: datetime.datetime) -> pd.DataFrame:

    bid_ask_costs, actual_trade_costs = get_costs_from_slippage(data, start_date, end_date)
    sampling_costs = get_average_half_spread_from_sampling(data, start_date, end_date)
    configured_costs = get_current_configured_spread_cost(data)



    combined = pd.concat([bid_ask_costs,
                          actual_trade_costs,
                          sampling_costs
                          ],
                                 axis=1)

    combined.columns = ["bid_ask_trades", "total_trades", "bid_ask_sampled"]

    worst = combined.max(axis=1)
    perc_difference = (worst - configured_costs) / configured_costs

    all_together = pd.concat([combined, worst, configured_costs, perc_difference], axis=1)
    all_together.columns = list(combined.columns) + ["Worst", "Configured", "% Difference"]

    all_together = all_together.sort_values("% Difference", ascending=False)

    return all_together

def get_average_half_spread_from_sampling(data, start_date, end_date):
    diag_prices = diagPrices(data)
    list_of_instruments = diag_prices.get_list_of_instruments_with_spread_data()

    spreads_as_list = [get_average_sampled_half_spread_for_instrument(data, instrument_code,
                                                                 start_date=start_date,
                                                                 end_date=end_date)
                       for instrument_code in list_of_instruments]

    spreads_as_df = pd.DataFrame(spreads_as_list, index = list_of_instruments)

    return spreads_as_df

def get_average_sampled_half_spread_for_instrument(data, instrument_code, start_date, end_date):
    diag_prices = diagPrices(data)
    raw_spreads = diag_prices.get_spreads(instrument_code)
    spreads_in_period = raw_spreads[start_date:end_date]
    average_half_spread = spreads_in_period.median(skipna=True) / 2.0
    return average_half_spread


def get_costs_from_slippage(data, start_date, end_date):
    list_of_orders = get_recent_broker_orders(data, start_date, end_date)

    raw_slippage = create_raw_slippage_df(list_of_orders)

    bid_ask_costs = get_average_half_spread_by_instrument_from_raw_slippage(raw_slippage, "bid_ask")
    actual_trade_costs = get_average_half_spread_by_instrument_from_raw_slippage(raw_slippage, "total_trading")

    return bid_ask_costs, actual_trade_costs

def get_average_half_spread_by_instrument_from_raw_slippage(raw_slippage, use_column = "bid_ask"):

    half_spreads_as_slippage = raw_slippage[use_column]
    half_spreads = - half_spreads_as_slippage
    half_spreads.index=raw_slippage.instrument_code
    half_spreads = half_spreads.astype(float)
    average_half_spread_by_code= half_spreads.groupby(level=0).median()

    return average_half_spread_by_code

def get_current_configured_spread_cost(data):
    diag_instruments = diagInstruments(data)
    list_of_instruments = diag_instruments.get_list_of_instruments()

    spreads_as_list = [get_configured_spread_cost_for_instrument(data, instrument_code)
                       for instrument_code in list_of_instruments]

    spreads_as_df = pd.Series(spreads_as_list, index = list_of_instruments)

    return spreads_as_df


def get_configured_spread_cost_for_instrument(data, instrument_code):
    diag_instruments = diagInstruments(data)
    meta_data = diag_instruments.get_meta_data(instrument_code)

    return meta_data.Slippage

def format_costs_data(costs_report_data: dict) -> list:

    formatted_output = []

    formatted_output.append(
        header("Costs report produced on %s from %s to %s" %
               (str(datetime.datetime.now()),
                costs_report_data['start_date'],
                costs_report_data['end_date']))
    )

    table1_df = costs_report_data['combined_df_costs']
    table1 = table("Costs", table1_df)
    formatted_output.append(table1)


    return formatted_output

