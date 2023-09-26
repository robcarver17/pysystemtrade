import numpy as np
import pandas as pd

from syscore.genutils import list_difference
from syscore.constants import arg_not_supplied
from syscore.dateutils import n_days_ago
from syscore.interactive.progress_bar import progressBar

from sysdata.data_blob import dataBlob
from sysproduction.data.contracts import dataContracts
from sysproduction.data.prices import diagPrices
from sysproduction.reporting.data.risk import get_risk_data_for_instrument


def get_liquidity_data_df(data: dataBlob, exclude_instruments: list = arg_not_supplied):
    diag_prices = diagPrices(data)

    instrument_list = diag_prices.get_list_of_instruments_with_contract_prices()
    if exclude_instruments is not arg_not_supplied:
        instrument_list = list_difference(instrument_list, exclude_instruments)

    print("Getting data... patience")
    p = progressBar(len(instrument_list))
    all_liquidity = []
    for instrument_code in instrument_list:
        p.iterate()
        liquidity_this_instrument = get_liquidity_dict_for_instrument_code(
            data, instrument_code
        )
        all_liquidity.append(liquidity_this_instrument)

    all_liquidity_df = pd.DataFrame(all_liquidity)
    all_liquidity_df.index = instrument_list
    all_liquidity_df["contracts"] = all_liquidity_df["contracts"].round(0)

    return all_liquidity_df


def get_liquidity_dict_for_instrument_code(data, instrument_code: str) -> dict:
    contract_volume = get_best_average_daily_volume_for_instrument(
        data, instrument_code
    )
    risk_per_contract = annual_risk_per_contract(data, instrument_code)
    volume_in_risk_terms_m = risk_per_contract * contract_volume / 1000000

    return dict(contracts=contract_volume, risk=volume_in_risk_terms_m)


def get_average_daily_volume_for_contract_object(
    data, contract_object, calendar_days_back: int = 30
):
    diag_prices = diagPrices(data)
    all_price_data = diag_prices.get_merged_prices_for_contract_object(contract_object)
    if all_price_data.empty:
        return 0.0
    volume = all_price_data.daily_volumes()
    date_cutoff = n_days_ago(calendar_days_back)
    recent_average_volume = volume[date_cutoff:].mean()

    return recent_average_volume


def get_best_average_daily_volume_for_instrument(data, instrument_code: str):

    data_contracts = dataContracts(data)
    contract_dates = data_contracts.get_all_sampled_contracts(instrument_code)

    volumes = [
        get_average_daily_volume_for_contract_object(data, contract_object)
        for contract_object in contract_dates
    ]

    if len(volumes) == 0:
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

    return risk_data["annual_risk_per_contract"]
