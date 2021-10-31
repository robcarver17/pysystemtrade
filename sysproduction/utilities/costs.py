import numpy as np
import pandas as pd

from syscore.dateutils import n_days_ago
from sysdata.data_blob import dataBlob
from sysproduction.data.currency_data import dataCurrency
from sysproduction.data.instruments import diagInstruments
from sysproduction.data.prices import diagPrices
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