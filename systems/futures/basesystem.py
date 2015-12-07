'''
This is a futures system

A system consists of a system, plus a config

These classes suffice for both live and simulation

We need to override them for live by adding 'write optimal position' and 'monitor message bus for new price'

We need to override them for simulation by adding 'generate fake trade list' and 'calculate p&l' methods 
'''
from sysdata.configdata import Config

from sysdata.csvdata import csvFuturesData

from systems.basesystem import System
from systems.futures.rawdata import FuturesRawData
from systems.forecasting import Rules
from systems.forecast_scale_cap import ForecastScaleCapFixed

def full_futures_system( data=None, config=None, trading_rules=None):
    """
    
    :param data: data object (defaults to reading from csv files)
    :type data: sysdata.data.Data, or anything that inherits from it
    
    :param config: Configuration object (defaults to futuresconfig.yaml in this directory)
    :type config: sysdata.configdata.Config
    
    :param trading_rules: Set of trading rules to use (defaults to set specified in config object)
    :param trading_rules: list or dict of TradingRules, or something that can be parsed to that
    
    >>> system=full_futures_system()
    >>> system
    System with subsystems: rawdata, rules
    >>> system.rules.get_raw_forecast("EDOLLAR", "ewmac2_8").tail(2)
                ewmac2_8
    2015-04-21  0.172416
    2015-04-22 -0.477559
    >>> system.rules.get_raw_forecast("EDOLLAR", "carry").tail(2)
                   carry
    2015-04-21  0.350892
    2015-04-22  0.350892
    """
    
    if data is None:
        data=csvFuturesData()
    
    if config is None:
        config=Config("futuresconfig.yaml")

    ## Set up the subsystems
    rawdata=FuturesRawData()
    rules=Rules(trading_rules)
    forecast_scale_cap=ForecastScaleCapFixed()
    
    return System( [rawdata, rules, forecast_scale_cap], data, config)

    
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()  