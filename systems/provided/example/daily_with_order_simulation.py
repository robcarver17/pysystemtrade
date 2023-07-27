### THIS IS AN EXAMPLE OF HOW TO USE A PROPER ORDER SIMULATOR RATHER THAN VECTORISED
###   P&L, FOR A SIMPLE TREND SYSTEM USING DAILY DATA WITH MARKET ORDERS

import matplotlib

matplotlib.use("TkAgg")

from syscore.constants import arg_not_supplied

# from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysdata.sim.db_futures_sim_data import dbFuturesSimData
from sysdata.config.configdata import Config

from systems.forecasting import Rules
from systems.basesystem import System

from systems.rawdata import RawData
from systems.forecast_combine import ForecastCombine
from systems.forecast_scale_cap import ForecastScaleCap
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.accounts.order_simulator.account_curve_order_simulator import (
    AccountWithOrderSimulator,
)
from systems.accounts.accounts_stage import Account


def futures_system(
    sim_data=arg_not_supplied,
    use_vanilla_accounting: bool = False,
    config_filename="systems.provided.example.daily_with_order_simulation.yaml",
):

    if sim_data is arg_not_supplied:
        sim_data = dbFuturesSimData()

    config = Config(config_filename)
    if use_vanilla_accounting:
        account = Account()
    else:
        account = AccountWithOrderSimulator()
    system = System(
        [
            account,
            Portfolios(),
            PositionSizing(),
            ForecastCombine(),
            ForecastScaleCap(),
            Rules(),
            RawData(),
        ],
        sim_data,
        config,
    )

    return system
