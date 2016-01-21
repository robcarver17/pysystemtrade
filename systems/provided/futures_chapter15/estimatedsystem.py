'''
This is a variation of the chapter 15 system which estimates rather than uses fixed parameters

A system consists of a system, plus a config

'''
from sysdata.csvdata import csvFuturesData
from sysdata.configdata import Config

from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombineEstimated
from systems.forecast_scale_cap import ForecastScaleCapEstimated
from systems.futures.rawdata import FuturesRawData
from systems.positionsizing import PositionSizing
from systems.portfolio import PortfoliosFixed
from systems.account import Account


def futures_system(data=None, config=None, trading_rules=None):
    """

    :param data: data object (defaults to reading from csv files)
    :type data: sysdata.data.Data, or anything that inherits from it

    :param config: Configuration object (defaults to futuresconfig.yaml in this directory)
    :type config: sysdata.configdata.Config

    :param trading_rules: Set of trading rules to use (defaults to set specified in config object)
    :param trading_rules: list or dict of TradingRules, or something that can be parsed to that

    >>> system=futures_system()
    >>> system
    System with stages: accounts, portfolio, positionSize, rawdata, combForecast, forecastScaleCap, rules
    >>> system.rules.get_raw_forecast("EDOLLAR", "ewmac2_8").dropna().head(2)
                ewmac2_8
    1983-10-10  0.695929
    1983-10-11 -0.604704

                ewmac2_8
    2015-04-21  0.172416
    2015-04-22 -0.477559
    >>> system.rules.get_raw_forecast("EDOLLAR", "carry").dropna().head(2)
                   carry
    1983-10-10  0.952297
    1983-10-11  0.854075

                   carry
    2015-04-21  0.350892
    2015-04-22  0.350892
    """

    if data is None:
        data = csvFuturesData()

    if config is None:
        config = Config(
            "systems.provided.futures_chapter15.futuresestimateconfig.yaml")

    rules = Rules(trading_rules)

    system = System([Account(), PortfoliosFixed(), PositionSizing(), FuturesRawData(), ForecastCombineEstimated(),
                     ForecastScaleCapEstimated(), rules], data, config)

    return system


if __name__ == '__main__':
    import doctest
    doctest.testmod()
