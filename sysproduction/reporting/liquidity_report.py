## Generate list of instruments ranked by liquidity: # of contracts per day and

import numpy as np
import datetime

from syscore.genutils import progressBar
from syscore.dateutils import two_weeks_ago
from syscore.objects import header, table, body_text, arg_not_supplied, missing_data

from sysdata.data_blob import dataBlob

from sysproduction.data.prices import diagPrices
from sysproduction.data.contracts import dataContracts
from sysproduction.reporting.risk_report import get_risk_data_for_instrument

import pandas as pd

def liquidity_report(data: dataBlob=arg_not_supplied):
    if data is arg_not_supplied:
        data = dataBlob()

    liquidity_report_data = get_liquidity_report_data(
        data)
    formatted_output = format_liquidity_data(liquidity_report_data)

    return formatted_output

def get_liquidity_report_data(data: dataBlob):
    all_liquidity_df = get_liquidity_data_df(data)
    liquidity_report_data = dict(all_liquidity_df = all_liquidity_df)

    return liquidity_report_data

def format_liquidity_data(liquidity_report_data: dict) -> list:

    formatted_output = []
    all_liquidity_df = liquidity_report_data['all_liquidity_df']
    formatted_output.append(
        header("Liquidity report produced on %s" %
               (str(datetime.datetime.now()))))

    table1_df = all_liquidity_df.sort_values("contracts")
    table1 = table(" Sorted by contracts: Less than 100 contracts a day is a problem", table1_df)
    formatted_output.append(table1)

    table2_df = all_liquidity_df.sort_values("risk")
    table2 = table("Sorted by risk: Less than $1.5 million of risk per day is a problem", table2_df)
    formatted_output.append(table2)


    return formatted_output


def get_liquidity_data_df(data: dataBlob):
    diag_prices = diagPrices(data)

    instrument_list = diag_prices.get_list_of_instruments_with_contract_prices()

    print("Getting data... patience")
    p = progressBar(len(instrument_list))
    all_liquidity = []
    for instrument_code in instrument_list:
        p.iterate()
        liquidity_this_instrument = get_liquidity_dict_for_instrument_code(data, instrument_code)
        all_liquidity.append(liquidity_this_instrument)

    all_liquidity_df = pd.DataFrame(all_liquidity)
    all_liquidity_df.index = instrument_list

    return all_liquidity_df


def get_liquidity_dict_for_instrument_code(data, instrument_code: str) -> dict:
    contract_volume = get_best_average_daily_volume_for_instrument(data, instrument_code)
    risk_per_contract = annual_risk_per_contract(data, instrument_code)
    volume_in_risk_terms_m = risk_per_contract * contract_volume / 1000000

    return dict(contracts = contract_volume, risk = volume_in_risk_terms_m)


def get_average_daily_volume_for_contract_object(data, contract_object):
    diag_prices = diagPrices(data)
    all_price_data = diag_prices.get_prices_for_contract_object(contract_object)
    if all_price_data.empty:
        return 0.0
    volume = all_price_data.daily_volumes()
    date_two_weeks_ago = two_weeks_ago()
    volume = volume[date_two_weeks_ago:].mean()

    return volume



def get_best_average_daily_volume_for_instrument(data, instrument_code: str):

    data_contracts = dataContracts(data)
    contract_dates = data_contracts.get_all_sampled_contracts(instrument_code)

    volumes = [get_average_daily_volume_for_contract_object(data, contract_object)
               for contract_object in contract_dates]

    if len(volumes)==0:
        ## can happen with brand new instruments not properly added
        return np.nan

    best_volume = max(volumes)

    return best_volume


def annual_risk_per_contract(data, instrument_code: str) -> float:
    try:
        risk_data = get_risk_data_for_instrument(data, instrument_code)
    except:
        ## can happen for brand new instruments not properly loaded
        return np.nan

    return risk_data['annual_risk_per_contract']
