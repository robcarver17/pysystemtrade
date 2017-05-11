from sysbrokers.baseClient import brokerClient
from ibapi import eclient


class ibClient(brokerClient):
    """
    Client specific to interactive brokers

    Overrides the methods in the base class specifically for IB

    """

    def __init__(self):
        pass
