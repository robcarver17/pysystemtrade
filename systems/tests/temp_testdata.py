
from systems.futures.rawdata import FuturesRawData    
from systems.rawdata import RawData
from sysdata.csvdata import csvFuturesData
from sysdata.configdata import Config
from systems.forecasting import Rules
from systems.forecast_scale_cap import ForecastScaleCapFixed
from systems.forecast_combine import ForecastCombineFixed
from systems.positionsizing import PositionSizing
from systems.portfolio import PortfoliosFixed

def get_test_object():
    """
    Returns some standard test data
    """
    data=csvFuturesData("sysdata.tests")
    rawdata=RawData()
    config=Config("systems.provided.example.exampleconfig.yaml")
    return (rawdata, data, config) 


def get_test_object_futures():
    """
    Returns some standard test data
    """
    data=csvFuturesData("sysdata.tests")
    rawdata=FuturesRawData()
    config=Config("systems.provided.example.exampleconfig.yaml")
    return (rawdata, data, config) 


def get_test_object_futures_with_rules():
    """
    Returns some standard test data
    """
    data=csvFuturesData("sysdata.tests")
    rawdata=FuturesRawData()
    rules=Rules()
    config=Config("systems.provided.example.exampleconfig.yaml")
    return (rules, rawdata, data, config) 

def get_test_object_futures_with_rules_and_capping():
    """
    Returns some standard test data
    """
    data=csvFuturesData("sysdata.tests")
    rawdata=FuturesRawData()
    rules=Rules()
    config=Config("systems.provided.example.exampleconfig.yaml")
    capobject=ForecastScaleCapFixed()
    return (capobject, rules, rawdata, data, config) 

def get_test_object_futures_with_comb_forecasts():
    """
    Returns some standard test data
    """
    data=csvFuturesData("sysdata.tests")
    rawdata=FuturesRawData()
    rules=Rules()
    config=Config("systems.provided.example.exampleconfig.yaml")
    capobject=ForecastScaleCapFixed()
    combobject=ForecastCombineFixed()
    return (combobject, capobject, rules, rawdata, data, config) 

def get_test_object_futures_with_pos_sizing():
    """
    Returns some standard test data
    """
    data=csvFuturesData("sysdata.tests")
    rawdata=FuturesRawData()
    rules=Rules()
    config=Config("systems.provided.example.exampleconfig.yaml")
    capobject=ForecastScaleCapFixed()
    combobject=ForecastCombineFixed()
    posobject=PositionSizing()
    return (posobject, combobject, capobject, rules, rawdata, data, config) 

def get_test_object_futures_with_portfolios():
    """
    Returns some standard test data
    """
    data=csvFuturesData("sysdata.tests")
    rawdata=FuturesRawData()
    rules=Rules()
    config=Config("systems.provided.example.exampleconfig.yaml")
    capobject=ForecastScaleCapFixed()
    combobject=ForecastCombineFixed()
    posobject=PositionSizing()
    portfolio=PortfoliosFixed()
    return (portfolio, posobject, combobject, capobject, rules, rawdata, data, config) 

