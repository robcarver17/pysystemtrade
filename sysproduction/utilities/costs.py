import datetime

import numpy as np
import pandas as pd

from syscore.dateutils import n_days_ago
from sysdata.data_blob import dataBlob
from sysproduction.data.currency_data import dataCurrency
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.prices import diagPrices
from sysproduction.utilities.trades import get_recent_broker_orders, create_raw_slippage_df
from sysproduction.utilities.risk_metrics import get_current_annualised_perc_stdev_for_instrument


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


def get_cash_cost_in_base_for_instrument(data: dataBlob, instrument_code: str):
    diag_instruments = diagInstruments(data)
    costs_object = diag_instruments.get_cost_object(instrument_code)
    blocks_traded = 1
    block_price_multiplier = get_block_size(data, instrument_code)
    price = recent_average_price(data, instrument_code)
    cost_instrument_ccy = costs_object.calculate_cost_instrument_currency(blocks_traded=blocks_traded,
                                                    block_price_multiplier=block_price_multiplier,
                                                    price=price)
    fx = last_currency_fx(data, instrument_code)
    cost_base_ccy = cost_instrument_ccy * fx

    return cost_base_ccy


def last_currency_fx(data: dataBlob, instrument_code: str) -> float:
    data_currency = dataCurrency(data)
    diag_instruments = diagInstruments(data)
    currency = diag_instruments.get_currency(instrument_code)
    fx_rate = data_currency.get_last_fx_rate_to_base(currency)

    return fx_rate


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
        perc =get_current_annualised_perc_stdev_for_instrument(data, instrument_code)
    except:
        ## can happen for brand new instruments not properly loaded
        return np.nan

    return perc


def get_combined_df_of_costs(data: dataBlob,
                             start_date: datetime.datetime,
                             end_date: datetime.datetime) -> pd.DataFrame:

    bid_ask_costs, actual_trade_costs,order_count = get_costs_from_slippage(data, start_date, end_date)
    sampling_costs, sample_count = get_average_half_spread_from_sampling(data, start_date, end_date)
    configured_costs = get_current_configured_spread_cost(data)

    combined = pd.concat([bid_ask_costs,
                          actual_trade_costs,
                          sampling_costs
                          ],
                                 axis=1)

    combined.columns = ["bid_ask_trades", "total_trades", "bid_ask_sampled"]

    estimate_with_data = best_estimate_from_cost_data(bid_ask_costs=bid_ask_costs,
                                            actual_trade_costs=actual_trade_costs,
                                            order_count=order_count,
                                            sampling_costs=sampling_costs,
                                            sample_count=sample_count,
                                            configured_costs=configured_costs)

    perc_difference = (estimate_with_data.estimate - configured_costs) / configured_costs

    all_together = pd.concat([combined,
                              estimate_with_data, configured_costs, perc_difference], axis=1)
    all_together.columns = list(combined.columns) + list(estimate_with_data.columns)+["Configured", "% Difference"]

    all_together = all_together.sort_values("% Difference", ascending=False)

    return all_together


def best_estimate_from_cost_data(bid_ask_costs: pd.Series,
                                 actual_trade_costs: pd.Series,
                                 order_count: pd.Series,
                                 sampling_costs: pd.Series,
                                 sample_count: pd.Series,
                                 configured_costs: pd.Series,
                                 trades_to_count_as_config = 10,
                                 samples_to_count_as_config = 150) -> pd.Series:

    worst_execution = pd.concat([bid_ask_costs, actual_trade_costs], axis=1)
    worst_execution = worst_execution.max(axis=1)

    all_weights = pd.concat([worst_execution,
                             order_count, sample_count,
                             sampling_costs, configured_costs], axis=1)


    all_weights.columns= ['trading', 'order_count',
                          'sample_count', 'sampled', 'configured']

    weight_on_trades = all_weights.order_count / trades_to_count_as_config
    weight_on_trades[weight_on_trades.isna()] = 0.0
    weight_on_trades[all_weights.trading.isna()] = 0.0
    all_weights.trading[all_weights.trading.isna()] = 0.0

    weight_on_samples = all_weights.sample_count / samples_to_count_as_config
    weight_on_samples[weight_on_samples.isna()] = 0.0
    weight_on_samples[all_weights.sampled.isna()] = 0.0
    all_weights.sampled[all_weights.sampled.isna()] = 0.0

    weight_on_config = pd.Series([1.0]*len(configured_costs), index= configured_costs.index)
    weight_on_config[weight_on_config.isna()] = 0.0
    weight_on_config[all_weights.configured.isna()] = 0.0

    weight_all = weight_on_samples + weight_on_trades + weight_on_config
    weight_all[weight_all==0.0] = np.nan

    weight_on_trades = weight_on_trades / weight_all
    weight_on_samples = weight_on_samples / weight_all
    weight_on_config = weight_on_config / weight_all

    weighted_trading = all_weights.trading*weight_on_trades
    weighted_samples = all_weights.sampled*weight_on_samples
    weighted_config = all_weights.configured*weight_on_config

    estimate = weighted_trading + weighted_samples + weighted_config

    estimate_with_data = pd.concat([weight_on_trades,
                                    weight_on_samples,
                                    weight_on_config, estimate], axis=1)
    estimate_with_data.columns = ['weight_trades',
                                  'weight_samples',
                                  'weight_config',
                                  'estimate']

    return estimate_with_data


def get_average_half_spread_from_sampling(data, start_date, end_date):
    diag_prices = diagPrices(data)
    list_of_instruments = diag_prices.get_list_of_instruments_with_spread_data()

    spreads_and_counts_as_list = [get_average_sampled_half_spread_and_count_for_instrument(data, instrument_code,
                                                                                start_date=start_date,
                                                                                end_date=end_date)
                       for instrument_code in list_of_instruments]

    spreads_as_df = pd.DataFrame(spreads_and_counts_as_list, index = list_of_instruments)

    return spreads_as_df.average_half_spread, spreads_as_df.count_of_spreads


def get_average_sampled_half_spread_and_count_for_instrument(data, instrument_code, start_date, end_date) -> dict:
    diag_prices = diagPrices(data)
    raw_spreads = diag_prices.get_spreads(instrument_code)
    spreads_in_period = raw_spreads[start_date:end_date]
    average_half_spread = spreads_in_period.median(skipna=True) / 2.0
    count_of_spreads = len(spreads_in_period)

    return dict(average_half_spread = average_half_spread, count_of_spreads = count_of_spreads)


def get_costs_from_slippage(data, start_date, end_date):
    list_of_orders = get_recent_broker_orders(data, start_date, end_date)

    raw_slippage = create_raw_slippage_df(list_of_orders)

    bid_ask_costs = get_average_half_spread_by_instrument_from_raw_slippage(raw_slippage, "bid_ask")
    actual_trade_costs = get_average_half_spread_by_instrument_from_raw_slippage(raw_slippage, "total_trading")

    order_count = order_count_by_instrument(list_of_orders)

    return bid_ask_costs, actual_trade_costs, order_count


def order_count_by_instrument(list_of_orders):
    return list_of_orders.instrument_code.value_counts()


def get_average_half_spread_by_instrument_from_raw_slippage(raw_slippage, use_column = "bid_ask"):

    half_spreads_as_slippage = raw_slippage[use_column]
    half_spreads = - half_spreads_as_slippage
    half_spreads.index=raw_slippage.instrument_code
    half_spreads = half_spreads.astype(float)
    average_half_spread_by_code= half_spreads.groupby(level=0).median()

    return average_half_spread_by_code


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