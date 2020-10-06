
from sysproduction.data.positions import diagPositions
from sysproduction.data.capital import dataCapital
from sysproduction.data.currency_data import currencyData
from sysproduction.data.instruments import diagInstruments


def get_positions_as_perc_of_capital( data):
    list_of_instruments = data_backtest.system.get_instrument_list()
    position_dict = dict([
        (instrument_code, get_current_position_for_instrument_code(data_backtest, data, instrument_code))
        for instrument_code in list_of_instruments])

    return position_dict


def get_current_position_for_instrument_code(data, strategy_name, instrument_code):
    diag_positions = diagPositions(data)
    current_position = diag_positions.get_position_for_strategy_and_instrument(strategy_name, instrument_code)

    return current_position

def get_perc_of_capital_position_size_for_instrument( data, strategy_name, instrument_code):
    capital = capital_for_strategy(data)

def capital_for_strategy(data_backtest, data):
    data_capital = dataCapital(data)
    capital = data_capital.get_capital_for_strategy(data_backtest.strategy_name)

    return capital

def get_notional_exposure_in_base_currency_for_instrument(data_backtest, data, instrument_code):
    currency_data = currencyData(data)
    diag_instruments = diagInstruments(data)
    diag_instruments.get_currency(instrument_code)

def get_notional_exposure_for_instrument(data_backtest, data, instrument_code):
    exposure_per_contract = get_exposure_per_contract(data_backtest, instrument_code)
    position = get_current_position_for_instrument_code(data_backtest, data, instrument_code)

    return exposure_per_contract * position

def get_exposure_per_contract(data_backtest, instrument_code):
    diag_instruments = diagInstruments(data)
    point_size = diag_instruments.get_point_size_base_currency(instrument_code)

    return point_size*100

def get_block_size(data_backtest, instrument_code):
    return data_backtest.system.positionSize.get_block_value(instrument_code)

