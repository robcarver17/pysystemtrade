from sysdata.csvdata import csvFuturesData
from sysdata.configdata import Config

from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombine
from systems.forecast_scale_cap import ForecastScaleCap
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.account import Account


def simplesystem(data=None, config=None, log_level="on"):
    """
    Example of how to 'wrap' a complete system
    """
    if config is None:
        config = Config("systems.provided.example.simplesystemconfig.yaml")
    if data is None:
        data = csvFuturesData()

    my_system = System([
        Account(), Portfolios(), PositionSizing(), ForecastCombine(),
        ForecastScaleCap(), Rules()
    ], data, config)

    my_system.set_logging_level(log_level)

    return my_system
