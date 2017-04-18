class brokerServer(object):
    """

    Broker server classes are called by the brokers server application (eg IB Gateway)

    We inherit from this and then write hooks from the servers native methods into the methods in this base class

    """

    def __init__(self):
        pass

    def action_to_take_when_time_set(self, time_received):
        print("Do something with time!")