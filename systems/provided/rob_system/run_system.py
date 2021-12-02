import matplotlib
matplotlib.use("TkAgg")

from syscore.objects import arg_not_supplied
#from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysdata.sim.db_futures_sim_data import dbFuturesSimData
from sysdata.config.configdata import Config

from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombine
from systems.provided.rob_system.forecastScaleCap import volAttenForecastScaleCap
from systems.provided.rob_system.rawdata import myFuturesRawData
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.provided.dynamic_small_system_optimise.portfolio_weights_stage import portfolioWeightsStage
from systems.provided.dynamic_small_system_optimise.optimised_positions_stage import optimisedPositions
from systems.provided.dynamic_small_system_optimise.risk import Risk
from systems.provided.dynamic_small_system_optimise.accounts_stage import accountForOptimisedStage

def futures_system(sim_data = arg_not_supplied,
                   config_filename = "systems.provided.rob_system.config.yaml"):

    if sim_data is arg_not_supplied:
        sim_data = dbFuturesSimData()

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

import pickle
system = futures_system()
list_of_rules = list(system.rules.trading_rules().keys())

"""
for rule in list_of_rules[21:]:
    pandl = system.accounts.pandl_for_trading_rule_unweighted(rule)
    perc = pandl.percent.as_ts
    with open("/home/rob/rule_perc_pandl_for_%s" % rule, "wb") as f:
        pickle.dump(perc, f)
"""

"""
all_pandl = dict()
for rule in list_of_rules:
    with open("/home/rob/rule_perc_pandl_for_%s" % rule, "rb") as f:
        perc = pickle.load(f)

    all_pandl[rule] = perc

import pandas as pd
all_pandl_df = pd.DataFrame(all_pandl)

system.cache.pickle("/home/rob/bigsystem.pck")
"""

import pickle
system = futures_system()
list_of_instruments = system.get_instrument_list()

"""
for code in list_of_instruments:
    pandl = system.accounts.pandl_for_subsystem(code)
    perc = pandl.percent.as_ts
    with open("/home/rob/instrument_perc_pandl_for_%s" % code, "wb") as f:
        pickle.dump(perc, f)
"""

all_pandl = dict()
for code in list_of_instruments:
    with open("/home/rob/instrument_perc_pandl_for_%s" % code, "rb") as f:
        perc = pickle.load(f)

    all_pandl[code] = perc

import pandas as pd
all_pandl_df = pd.DataFrame(all_pandl)

[[('min', '-15.76'), ('max', '12.82'), ('median', '0.1137'), ('mean', '0.1383'), ('std', '1.703'), ('skew', '-0.1628'), ('ann_mean', '35.39'), ('ann_std', '27.25'), ('sharpe', '1.299'), ('sortino', '1.778'), ('avg_drawdown', '-12.21'), ('time_in_drawdown', '0.9154'), ('calmar', '0.592'), ('avg_return_to_drawdown', '2.898'), ('avg_loss', '-1.162'), ('avg_gain', '1.246'), ('gaintolossratio', '1.072'), ('profitfactor', '1.259'), ('hitrate', '0.54'), ('t_stat', '9.439'), ('p_value', '4.352e-21')], ('You can also plot / print:', ['rolling_ann_std', 'drawdown', 'curve', 'percent'])]