from sysbrokers.baseServer import brokerServer
from ibapi import wrapper


class ibServer(wrapper.EWrapper):
    """
    Server specific to interactive brokers

    Overrides the methods in the base class specifically for IB

    """

    def __init__(self):
        pass
