from systems.account import Account
from systems.portfolio import Portfolios
from systems.futures.rawdata import FuturesRawData
from systems.rawdata import RawData
from sysdata.csvdata import csvFuturesData
from sysdata.configdata import Config
from systems.forecasting import Rules
from systems.forecast_scale_cap import ForecastScaleCap
from systems.forecast_combine import ForecastCombine
from systems.positionsizing import PositionSizing


def get_test_object():
    """
    Returns some standard test data
    """
    data = csvFuturesData("sysdata.tests")
    rawdata = RawData()
    config = Config("systems.provided.example.exampleconfig.yaml")
    return (rawdata, data, config)


def get_test_object_futures():
    """
    Returns some standard test data
    """
    data = csvFuturesData("sysdata.tests")
    rawdata = FuturesRawData()
    config = Config("systems.provided.example.exampleconfig.yaml")
    return (rawdata, data, config)


def get_test_object_futures_with_rules():
    """
    Returns some standard test data
    """
    data = csvFuturesData("sysdata.tests")
    rawdata = FuturesRawData()
    rules = Rules()
    config = Config("systems.provided.example.exampleconfig.yaml")
    return (rules, rawdata, data, config)


def get_test_object_futures_with_rules_and_capping():
    """
    Returns some standard test data
    """
    data = csvFuturesData("sysdata.tests")
    rawdata = FuturesRawData()
    rules = Rules()
    config = Config("systems.provided.example.exampleconfig.yaml")
    capobject = ForecastScaleCap()
    return (capobject, rules, rawdata, data, config)


def get_test_object_futures_with_comb_forecasts():
    """
    Returns some standard test data
    """
    data = csvFuturesData("sysdata.tests")
    rawdata = FuturesRawData()
    rules = Rules()
    config = Config("systems.provided.example.exampleconfig.yaml")
    capobject = ForecastScaleCap()
    combobject = ForecastCombine()
    return (combobject, capobject, rules, rawdata, data, config)


def get_test_object_futures_with_pos_sizing():
    """
    Returns some standard test data
    """
    data = csvFuturesData("sysdata.tests")
    rawdata = FuturesRawData()
    rules = Rules()
    config = Config("systems.provided.example.exampleconfig.yaml")
    capobject = ForecastScaleCap()
    combobject = ForecastCombine()
    posobject = PositionSizing()
    return (posobject, combobject, capobject, rules, rawdata, data, config)


def get_test_object_futures_with_portfolios():
    """
    Returns some standard test data
    """
    data = csvFuturesData("sysdata.tests")
    rawdata = FuturesRawData()
    rules = Rules()
    config = Config("systems.provided.example.exampleconfig.yaml")
    capobject = ForecastScaleCap()
    combobject = ForecastCombine()
    posobject = PositionSizing()
    portfolio = Portfolios()
    return (portfolio, posobject, combobject, capobject, rules, rawdata, data,
            config)


def get_test_object_futures_with_rules_and_capping_estimate():
    """
    Returns some standard test data
    """
    data = csvFuturesData("sysdata.tests")
    rawdata = FuturesRawData()
    rules = Rules()
    config = Config("systems.provided.example.estimateexampleconfig.yaml")
    capobject = ForecastScaleCap()
    account = Account()
    return (account, capobject, rules, rawdata, data, config)


def get_test_object_futures_with_pos_sizing_estimates():
    """
    Returns some standard test data
    """
    data = csvFuturesData("sysdata.tests")
    rawdata = FuturesRawData()
    rules = Rules()
    config = Config("systems.provided.example.estimateexampleconfig.yaml")
    capobject = ForecastScaleCap()
    combobject = ForecastCombine()
    posobject = PositionSizing()
    account = Account()
    return (account, posobject, combobject, capobject, rules, rawdata, data,
            config)
