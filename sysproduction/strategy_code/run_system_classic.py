"""
this:

- gets capital from the database (earmarked with a strategy name)
- runs a backtest using that capital level, and mongodb data
- gets the final positions and position buffers
- writes these into a table (earmarked with a strategy name)


"""

from syscore.objects import success, missing_data

from sysdata.configdata import Config
from sysdata.production.optimal_positions import bufferedOptimalPositions

from sysproduction.data.currency_data import currencyData
from sysproduction.data.capital import dataCapital
from sysproduction.data.contracts import diagContracts
from sysproduction.data.positions import dataOptimalPositions
from sysproduction.data.sim_data import dataSimData

from sysproduction.diagnostic.backtest_state import store_backtest_state

from syslogdiag.log import logtoscreen

from systems.provided.futures_chapter15.basesystem import futures_system


class runSystemClassic(object):
    def __init__(
        self,
        data,
        strategy_name,
        backtest_config_filename="systems.provided.futures_chapter15.futures_config.yaml",
    ):
        self.data = data
        self.strategy_name = strategy_name
        self.backtest_config_filename = backtest_config_filename

    def run_system_classic(self):
        strategy_name = self.strategy_name
        data = self.data

        capital_data = dataCapital(data)
        capital_value = capital_data.get_capital_for_strategy(strategy_name)
        if capital_data is missing_data:
            # critical log will send email
            error_msg = (
                "Capital data is missing for %s: can't run backtest" %
                strategy_name)
            data.log.critical(error_msg)
            raise Exception(error_msg)

        currency_data = currencyData(data)
        base_currency = currency_data.get_base_currency()

        system = self.system_method(
            notional_trading_capital=capital_value, base_currency=base_currency
        )

        updated_buffered_positions(data, strategy_name, system)

        store_backtest_state(data, system, strategy_name=strategy_name)

        return success

    def system_method(self, notional_trading_capital=None, base_currency=None):
        data = self.data
        backtest_config_filename = self.backtest_config_filename

        system = production_classic_futures_system(
            data,
            backtest_config_filename,
            log=data.log,
            notional_trading_capital=notional_trading_capital,
            base_currency=base_currency,
        )

        return system


def production_classic_futures_system(
    data,
    config_filename,
    log=logtoscreen("futures_system"),
    notional_trading_capital=None,
    base_currency=None,
):

    log_level = "on"

    # ugly but once you've established a pattern...
    sim_data = dataSimData(data).sim_data()
    config = Config(config_filename)

    # Overwrite capital
    if notional_trading_capital is not None:
        config.notional_trading_capital = notional_trading_capital

    if base_currency is not None:
        config.base_currency = base_currency

    system = futures_system(data=sim_data, config=config)
    system.log = log

    system.set_logging_level(log_level)

    return system


def updated_buffered_positions(data, strategy_name, system):
    log = data.log

    data_optimal_positions = dataOptimalPositions(data)

    list_of_instruments = system.get_instrument_list()
    for instrument_code in list_of_instruments:
        lower_buffer, upper_buffer = get_position_buffers_from_system(
            system, instrument_code
        )
        position_entry = construct_position_entry(
            data, system, instrument_code, lower_buffer, upper_buffer
        )
        data_optimal_positions.update_optimal_position_for_strategy_and_instrument(
            strategy_name, instrument_code, position_entry)
        log.msg(
            "New buffered positions %.3f %.3f" %
            (position_entry.lower_position,
             position_entry.upper_position),
            instrument_code=instrument_code,
        )

    return success


def get_position_buffers_from_system(system, instrument_code):
    buffers = system.portfolio.get_buffers_for_position(
        instrument_code
    )  # get the upper and lower edges of the buffer
    lower_buffer = buffers.iloc[-1].bot_pos
    upper_buffer = buffers.iloc[-1].top_pos

    return lower_buffer, upper_buffer


def construct_position_entry(
        data,
        system,
        instrument_code,
        lower_buffer,
        upper_buffer):
    diag_contracts = diagContracts(data)
    reference_price = system.rawdata.get_daily_prices(instrument_code).iloc[-1]
    reference_contract = diag_contracts.get_priced_contract_id(instrument_code)
    position_entry = bufferedOptimalPositions(
        lower_buffer, upper_buffer, reference_price, reference_contract
    )

    return position_entry
