
from systems.futures.rawdata import FuturesRawData    
from systems.rawdata import RawData
from syscore.fileutils import get_pathname_for_package
from sysdata.csvdata import csvFuturesData
from sysdata.configdata import Config
from systems.forecasting import Rules
from systems.forecast_scale_cap import ForecastScaleCapFixed
from systems.forecast_combine import ForecastCombineFixed
from systems.positionsizing import PositionSizing

def get_test_object():
    """
    Returns some standard test data
    """
    datapath=get_pathname_for_package("sysdata", ["tests"])
    data=csvFuturesData(datapath=datapath)
    rawdata=RawData()
    config_filename=get_pathname_for_package("systems", ["provided", "example", "exampleconfig.yaml"])
    config=Config(config_filename)
    return (rawdata, data, config) 


def get_test_object_futures():
    """
    Returns some standard test data
    """
    datapath=get_pathname_for_package("sysdata", ["tests"])
    data=csvFuturesData(datapath=datapath)
    rawdata=FuturesRawData()
    config_filename=get_pathname_for_package("systems", ["provided", "example", "exampleconfig.yaml"])
    config=Config(config_filename)
    return (rawdata, data, config) 


def get_test_object_futures_with_rules():
    """
    Returns some standard test data
    """
    datapath=get_pathname_for_package("sysdata", ["tests"])
    data=csvFuturesData(datapath=datapath)
    rawdata=FuturesRawData()
    rules=Rules()
    config_filename=get_pathname_for_package("systems", ["provided", "example", "exampleconfig.yaml"])
    config=Config(config_filename)
    return (rules, rawdata, data, config) 

def get_test_object_futures_with_rules_and_capping():
    """
    Returns some standard test data
    """
    datapath=get_pathname_for_package("sysdata", ["tests"])
    data=csvFuturesData(datapath=datapath)
    rawdata=FuturesRawData()
    rules=Rules()
    config_filename=get_pathname_for_package("systems", ["provided", "example", "exampleconfig.yaml"])
    config=Config(config_filename)
    capobject=ForecastScaleCapFixed()
    return (capobject, rules, rawdata, data, config) 

def get_test_object_futures_with_comb_forecasts():
    """
    Returns some standard test data
    """
    datapath=get_pathname_for_package("sysdata", ["tests"])
    data=csvFuturesData(datapath=datapath)
    rawdata=FuturesRawData()
    rules=Rules()
    config_filename=get_pathname_for_package("systems", ["provided", "example", "exampleconfig.yaml"])
    config=Config(config_filename)
    capobject=ForecastScaleCapFixed()
    combobject=ForecastCombineFixed()
    return (combobject, capobject, rules, rawdata, data, config) 

def get_test_object_futures_with_pos_sizing():
    """
    Returns some standard test data
    """
    datapath=get_pathname_for_package("sysdata", ["tests"])
    data=csvFuturesData(datapath=datapath)
    rawdata=FuturesRawData()
    rules=Rules()
    config_filename=get_pathname_for_package("systems", ["provided", "example", "exampleconfig.yaml"])
    config=Config(config_filename)
    capobject=ForecastScaleCapFixed()
    combobject=ForecastCombineFixed()
    posobject=PositionSizing()
    return (posobject, combobject, capobject, rules, rawdata, data, config) 

