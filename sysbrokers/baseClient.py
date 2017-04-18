class brokerClient(object):
    """

    Broker server classes are called by the brokers server application (eg IB Gateway)

    We inherit from this for specific brokers and over ride the methods in the base class to ensure a consistent API

    """

    def __init__(self):
        pass

    def speakingClock(self):
        print("Method needs to be overriden to do anything interesting")
