import pandas as pd

def nice_format_roll_table(roll_table: pd.DataFrame) -> pd.DataFrame:
    roll_table.volume_priced = roll_table.volume_priced.astype(float)
    roll_table.volume_priced = roll_table.volume_priced.round(3)
    roll_table.volume_fwd = roll_table.volume_fwd.astype(float)
    roll_table.volume_fwd = roll_table.volume_fwd.round(3)
    return roll_table

def nice_format_slippage_table(slippage_table: pd.DataFrame) -> pd.DataFrame:
    slippage_table.Difference = slippage_table.Difference.round(1)
    slippage_table.bid_ask_trades = slippage_table.bid_ask_trades.round(4)
    slippage_table.total_trades = slippage_table.total_trades.round(4)
    slippage_table.bid_ask_sampled = slippage_table.bid_ask_sampled.round(4)
    slippage_table.weight_trades = slippage_table.weight_trades.round(2)
    slippage_table.weight_samples = slippage_table.weight_samples.round(2)
    slippage_table.weight_config = slippage_table.weight_config.round(2)
    slippage_table.estimate = slippage_table.estimate.round(4)
    slippage_table.Configured = slippage_table.Configured.round(4)

    return slippage_table

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