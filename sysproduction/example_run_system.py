"""
this:

- gets capital from the database (earmarked with a strategy name)
- runs a backtest using that capital level, and mongodb data
- gets the final positions and position buffers
- writes these into a table (earmarked with a strategy name)


"""


from sysproduction.data.get_data import dataBlob
from sysproduction.data.capital import get_capital
from sysproduction.diagnostic.backtest_state import store_backtest_state
from syslogdiag.log import logToMongod as logger
from sysdata.mongodb.mongo_connection import mongoDb

from syscore.objects import success

from sysdata.arctic.arctic_and_mongo_sim_futures_data import arcticFuturesSimData
from sysdata.production.optimal_positions import bufferedOptimalPositions
from sysdata.configdata import Config

from systems.provided.futures_chapter15.basesystem import futures_system

strategy_name="example_system"
backtest_config_filename="systems.provided.futures_chapter15.futures_config.yaml"
account_currency = "GBP"

def run_system():

    with mongoDb() as mongo_db, \
            logger("runSystem", mongo_db=mongo_db, strategy = strategy_name) as log:

        data = dataBlob(mongo_db=mongo_db, log=log)

        capital_value = get_capital(data, strategy_name)

        system = production_futures_system(backtest_config_filename,
                                            log=log, notional_trading_capital=capital_value,
                                           base_currency=account_currency)

        updated_buffered_positions(data, strategy_name, system)

        store_backtest_state(data, system, strategy_name=strategy_name,
                             backtest_config_filename=backtest_config_filename)
        return success


def production_futures_system(config_filename, log=logger("futures_system"),
                   notional_trading_capital=1000000, base_currency="USD"):
    """

    :param data: data object (defaults to reading from csv files)
    :type data: sysdata.data.simData, or anything that inherits from it

    :param config: Configuration object (defaults to futuresconfig.yaml in this directory)
    :type config: sysdata.configdata.Config

    :param log_level: How much logging to do
    :type log_level: str


    """
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

    list_of_instruments = system.get_instrument_list()
    for instrument_code in list_of_instruments:
        try:
            position_entry = get_position_buffers_from_system(system, instrument_code)
            optimal_position_data.update_optimal_position_for_strategy_and_instrument(strategy_name, instrument_code, position_entry)
            data.log.msg("New buffered positions %.3f %.3f" %
                         (position_entry.lower_position,
                          position_entry.upper_position), instrument_code=instrument_code)
        except Exception as e:
            data.log.warn("Couldn't get or update buffered positions error %s" % e, instrument_code=instrument_code)

    return success

def get_position_buffers_from_system(system, instrument_code):
    buffers = system.portfolio.get_buffers_for_position(
        instrument_code)  ## get the upper and lower edges of the buffer
    lower_buffer = buffers.iloc[-1].bot_pos
    upper_buffer = buffers.iloc[-1].top_pos

    position_entry = bufferedOptimalPositions(lower_buffer, upper_buffer)

    return position_entry


