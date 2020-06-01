"""
this:

- gets capital from the database (earmarked with a strategy name)
- runs a backtest using that capital level, and mongodb data
- gets the final positions and position buffers
- writes these into a table (earmarked with a strategy name)


"""




from syscore.objects import success, missing_data

from sysdata.arctic.arctic_and_mongo_sim_futures_data import arcticFuturesSimData
from sysdata.configdata import Config
from sysdata.production.optimal_positions import bufferedOptimalPositions

from sysproduction.data.currency_data import currencyData
from sysproduction.data.capital import dataCapital
from sysproduction.data.contracts import diagContracts

from sysproduction.diagnostic.backtest_state import store_backtest_state


from syslogdiag.log import logtoscreen

from systems.provided.futures_chapter15.basesystem import futures_system


def run_system_classic(strategy_name, data,
               backtest_config_filename="systems.provided.futures_chapter15.futures_config.yaml"):

        capital_data = dataCapital()
        capital_value = capital_data.get_capital_for_strategy(strategy_name)
        if capital_data is missing_data:
            ## critical log will send email
            error_msg = "Capital data is missing for %s: can't run backtest" % strategy_name
            data.log.critical(error_msg)
            raise Exception(error_msg)

        currency_data = currencyData(data)
        base_currency = currency_data.get_base_currency()

        system = production_classic_futures_system(backtest_config_filename,
                                            log=data.log, notional_trading_capital=capital_value,
                                           base_currency=base_currency)

        updated_buffered_positions(data, strategy_name, system)

        store_backtest_state(data, system, strategy_name=strategy_name,
                             backtest_config_filename=backtest_config_filename)
        return success


def production_classic_futures_system(config_filename, log=logtoscreen("futures_system"),
                   notional_trading_capital=1000000, base_currency="USD"):

    log_level = "on"
    data = arcticFuturesSimData()

    config = Config(
            config_filename)

    # Overwrite capital
    config.notional_trading_capital = notional_trading_capital
    config.base_currency = base_currency

    system = futures_system(data=data, config=config)
    system.log = log

    system.set_logging_level(log_level)

    return system



def updated_buffered_positions(data, strategy_name, system):
    data.add_class_list("mongoOptimalPositionData")
    optimal_position_data = data.mongo_optimal_position

    diag_contracts = diagContracts()

    list_of_instruments = system.get_instrument_list()
    for instrument_code in list_of_instruments:
        try:
            lower_buffer, upper_buffer = get_position_buffers_from_system(system, instrument_code)
            position_entry = construct_position_entry(diag_contracts, system, instrument_code, lower_buffer, upper_buffer)
            optimal_position_data.update_optimal_position_for_strategy_and_instrument(strategy_name, instrument_code, position_entry)
            data.log.msg("New buffered positions %.3f %.3f" %
                         (position_entry.lower_position,
                          position_entry.upper_position), instrument_code=instrument_code)
        except Exception as e:
            data.log.critical("Couldn't get or update buffered positions error %s" % e, instrument_code=instrument_code)

    return success

def get_position_buffers_from_system(system, instrument_code):
    buffers = system.portfolio.get_buffers_for_position(
        instrument_code)  ## get the upper and lower edges of the buffer
    lower_buffer = buffers.iloc[-1].bot_pos
    upper_buffer = buffers.iloc[-1].top_pos

    return lower_buffer, upper_buffer

def construct_position_entry(diag_contracts, system, instrument_code, lower_buffer, upper_buffer):
    reference_price = system.rawdata.get_daily_prices(instrument_code).iloc[-1]
    reference_contract = diag_contracts.get_priced_contract_id(instrument_code)
    position_entry = bufferedOptimalPositions(lower_buffer, upper_buffer, reference_price, reference_contract)

    return position_entry

