
from syscore.objects import arg_not_supplied

from sysdata.data_blob import dataBlob

from sysproduction.data.sim_data import
from sysproduction.strategy_code.run_dynamic_optimised_system import runSystemCarryTrendDynamic

from syslogdiag.log_to_screen import logtoscreen

from systems.basesystem import System


def production_carry_trend_dynamic_system(
    data: dataBlob,
    config_filename: str,
    log=logtoscreen("futures_system"),
    notional_trading_capital: float=arg_not_supplied,
    base_currency: str=arg_not_supplied,
) -> System:

    log_level = "on"
    data = dataBlob()

    # Overwrite capital and base currency
    if notional_trading_capital is not arg_not_supplied:
        config.notional_trading_capital = notional_trading_capital

    if base_currency is not arg_not_supplied:
        config.base_currency = base_currency

    system = futures_system(data=sim_data, config=config)
    system._log = log

    system.set_logging_level(log_level)

    return system

from sysdata.config.configdata import Config

from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombine
from private.systems.carrytrend.forecastScaleCap import volAttenForecastScaleCap
from private.systems.carrytrend.rawdata import myFuturesRawData
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.provided.dynamic_small_system_optimise.portfolio_weights_stage import portfolioWeightsStage
from systems.provided.dynamic_small_system_optimise.optimised_positions_stage import optimisedPositions
from systems.provided.dynamic_small_system_optimise.risk import Risk
from systems.provided.dynamic_small_system_optimise.accounts_stage import accountForOptimisedStage

def futures_system(sim_data = arg_not_supplied, config_filename = ""):
    if sim_data is arg_not_supplied:

    sim_data = get_sim_data_object_for_production(data)
    config = Config(config_filename)

    system = System(
        [
            Risk(),
            accountForOptimisedStage(),
            optimisedPositions(),
            portfolioWeightsStage(),
            Portfolios(),
            PositionSizing(),
            myFuturesRawData(),
            ForecastCombine(),
            volAttenForecastScaleCap(),
            Rules(),

        ],
        data,
        config,
    )
    system.set_logging_level("on")

    return system



