
from systems.rawdata import RawData
from sysdata.csvdata import csvFuturesData
from sysdata.configdata import Config


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
    config = Config("systems.provided.example.exampleconfig.yaml")
    return (data, config)
