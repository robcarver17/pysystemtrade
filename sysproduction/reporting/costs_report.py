## Generate expected spread from actual trades, and sampled spreads
import datetime
import pandas as pd
import numpy as np
from sysdata.data_blob import dataBlob

from syscore.dateutils import n_days_ago

from sysproduction.data.prices import diagPrices
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.positions import annonate_df_index_with_positions_held
from sysproduction.reporting.trades_report import create_raw_slippage_df, get_recent_broker_orders
from sysproduction.reporting.risk_report import get_risk_data_for_instrument

from syscore.objects import header, table, arg_not_supplied


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
    combined_df_costs = annonate_df_index_with_positions_held(data=data,
                                                              pd_df=combined_df_costs)

    table_of_SR_costs =get_table_of_SR_costs(data)
    table_of_SR_costs = table_of_SR_costs.round(5)
    table_of_SR_costs = annonate_df_index_with_positions_held(data=data,
                                                              pd_df=table_of_SR_costs)

    costs_report_data = dict(combined_df_costs = combined_df_costs,
                             start_date = start_date,
                             end_date = end_date,
                             table_of_SR_costs = table_of_SR_costs)

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

def get_table_of_SR_costs(data):
    diag_prices = diagPrices(data)
    list_of_instruments = diag_prices.get_list_of_instruments_in_multiple_prices()
    SR_costs = dict(
        [
            (instrument_code, get_SR_cost_for_instrument(data, instrument_code))
            for instrument_code in list_of_instruments
        ]
    )
    SR_costs = pd.Series(SR_costs)
    SR_costs = SR_costs.to_frame('SR_cost')
    SR_costs = SR_costs.sort_values('SR_cost', ascending=False)

    return SR_costs

def get_SR_cost_for_instrument(data: dataBlob, instrument_code: str):
    print("Costs for %s" % instrument_code)
    percentage_cost = get_percentage_cost_for_instrument(data, instrument_code)
    avg_annual_vol_perc = get_percentage_ann_stdev(data, instrument_code)

    # cost per round trip
    SR_cost = 2.0 * percentage_cost / avg_annual_vol_perc

    return SR_cost


def get_percentage_cost_for_instrument(data: dataBlob, instrument_code: str):
    diag_instruments = diagInstruments(data)
    costs_object = diag_instruments.get_cost_object(instrument_code)
    blocks_traded = 1
    block_price_multiplier = get_block_size(data, instrument_code)
    price = recent_average_price(data, instrument_code)
    percentage_cost = \
        costs_object.calculate_cost_percentage_terms(blocks_traded=blocks_traded,
                                                     block_price_multiplier=block_price_multiplier,
                                                     price=price)

    return percentage_cost

def recent_average_price(data: dataBlob, instrument_code: str) -> float:
    diag_prices = diagPrices(data)
    prices = diag_prices.get_adjusted_prices(instrument_code)
    if len(prices)==0:
        return np.nan
    one_year_ago = n_days_ago(365)
    recent_prices= prices[one_year_ago:]

    return recent_prices.mean(skipna=True)


def get_block_size(data, instrument_code):
    diag_instruments = diagInstruments(data)
    return diag_instruments.get_point_size(instrument_code)

def get_percentage_ann_stdev(data, instrument_code):
    try:
        risk_data = get_risk_data_for_instrument(data, instrument_code)
    except:
        ## can happen for brand new instruments not properly loaded
        return np.nan

    return risk_data['annual_perc_stdev']/100.0


def format_costs_data(costs_report_data: dict) -> list:

    formatted_output = []

    formatted_output.append(
        header("Costs report produced on %s from %s to %s" %
               (str(datetime.datetime.now()),
                costs_report_data['start_date'],
                costs_report_data['end_date']))
    )

    table1_df = costs_report_data['combined_df_costs']
    table1 = table("Check of slippage", table1_df)
    formatted_output.append(table1)

    table2_df = costs_report_data['table_of_SR_costs']
    table2 = table("SR costs (using stored slippage): more than 0.01 means panic", table2_df)
    formatted_output.append(table2)


    return formatted_output

