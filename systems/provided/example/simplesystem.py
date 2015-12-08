from sysdata.csvdata import csvFuturesData
from sysdata.configdata import Config
from syscore.fileutils import get_pathname_for_package

from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombineFixed
from systems.forecast_scale_cap import ForecastScaleCapFixed
from systems.futures.rawdata import FuturesRawData
from systems.positionsizing import PositionSizing
from systems.portfolio import PortfoliosFixed
from systems.account import Account


def simplesystem(data=None, config=None):
    """
    Example of how to 'wrap' a complete system
    """
    if config is None:
        config=Config(get_pathname_for_package("systems", ["provided", "example", "simplesystemconfig.yaml"]))
    if data is None:
        data=csvFuturesData()

    my_system=System([Account(), PortfoliosFixed(), PositionSizing(), FuturesRawData(), ForecastCombineFixed(), ForecastScaleCapFixed(), Rules()
                      ], data, config)

    return my_system


