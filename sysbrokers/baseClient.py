from sysbrokers.baseServer import finishableQueue

class brokerClient(object):
    """

    Broker server classes are called by the brokers server application (eg IB Gateway)

    We inherit from this for specific brokers and over ride the methods in the base class to ensure a consistent API

    """


    def broker_get_fx_data(self, ccy1, ccy2="USD"):
        raise NotImplementedError

