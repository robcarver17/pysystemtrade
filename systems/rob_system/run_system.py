
from syscore.objects import arg_not_supplied
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysdata.config.configdata import Config

from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombine
from systems.rob_system.forecastScaleCap import volAttenForecastScaleCap
from systems.rob_system.rawdata import myFuturesRawData
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.provided.dynamic_small_system_optimise.portfolio_weights_stage import portfolioWeightsStage
from systems.provided.dynamic_small_system_optimise.optimised_positions_stage import optimisedPositions
from systems.provided.dynamic_small_system_optimise.risk import Risk
from systems.provided.dynamic_small_system_optimise.accounts_stage import accountForOptimisedStage

def futures_system(sim_data = arg_not_supplied,
                   config_filename = "systems.rob_system.config.yaml"):
    
    if sim_data is arg_not_supplied:
        sim_data = csvFuturesSimData()

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
        sim_data,
        config,
    )
    system.set_logging_level("on")

    return system



