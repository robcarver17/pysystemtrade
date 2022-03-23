import pandas as pd


def nice_format_liquidity_table(liquidity_table: pd.DataFrame) -> pd.DataFrame:
    liquidity_table = liquidity_table.dropna()
    liquidity_table.contracts = liquidity_table.contracts.astype(int)
    liquidity_table.risk = liquidity_table.risk.round(2)
    return liquidity_table


def nice_format_instrument_risk_table(instrument_risk_data: pd.DataFrame) -> pd.DataFrame:
    instrument_risk_data.daily_price_stdev = instrument_risk_data.daily_price_stdev.round(3)
    instrument_risk_data.annual_price_stdev = instrument_risk_data.annual_price_stdev.round(3)
    instrument_risk_data.price = instrument_risk_data.price.round(2)
    instrument_risk_data.daily_perc_stdev = instrument_risk_data.daily_perc_stdev.round(2)
    instrument_risk_data.annual_perc_stdev = instrument_risk_data.annual_perc_stdev.round(1)
    instrument_risk_data.point_size_base = instrument_risk_data.point_size_base.round(1)
    instrument_risk_data.contract_exposure = instrument_risk_data.contract_exposure.astype(int)
    instrument_risk_data.daily_risk_per_contract = instrument_risk_data.daily_risk_per_contract.astype(int)
    instrument_risk_data.annual_risk_per_contract = instrument_risk_data.annual_risk_per_contract.astype(int)
    instrument_risk_data.position = instrument_risk_data.position.astype(int)
    instrument_risk_data.capital = instrument_risk_data.capital.astype(int)
    instrument_risk_data.exposure_held_perc_capital = instrument_risk_data.exposure_held_perc_capital.round(1)
    instrument_risk_data.annual_risk_perc_capital = instrument_risk_data.annual_risk_perc_capital.round(1)

    return instrument_risk_data