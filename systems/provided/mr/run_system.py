import matplotlib

matplotlib.use("TkAgg")

from syscore.constants import arg_not_supplied

# from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysdata.sim.db_futures_sim_data import dbFuturesSimData
from sysdata.config.configdata import Config

from systems.forecasting import Rules
from systems.basesystem import System
from systems.provided.mr.forecast_combine import MrForecastCombine
from systems.provided.attenuate_vol.vol_attenuation_forecast_scale_cap import (
    volAttenForecastScaleCap,
)
from systems.provided.mr.rawdata import MrRawData
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.provided.mr.accounts import MrAccount


def futures_system(
    sim_data=arg_not_supplied, config_filename="systems.provided.mr.config.yaml"
):

    if sim_data is arg_not_supplied:
        sim_data = dbFuturesSimData()

    config = Config(config_filename)

    system = System(
        [
            MrAccount(),
            Portfolios(),
            PositionSizing(),
            MrRawData(),
            MrForecastCombine(),
            volAttenForecastScaleCap(),
            Rules(),
        ],
        sim_data,
        config,
    )
    system.set_logging_level("on")

    return system
