"""
Classes to create instances of connections

Connections contain plugs to data and brokers, so the two can talk to each other
"""

from collections import namedtuple
from threading import Thread

from sysbrokers.IB.ibClient import ibClient
from sysbrokers.IB.ibServer import ibServer
from syslogdiag.log import logtoscreen

ibConnectionConfig = namedtuple('ibconnection', ['ipaddress', 'portid', 'client'])

class connectionIB(ibClient, ibServer):
    """
    Connection object for connecting IB
    (A database plug in will need to be added for streaming prices)
    """

    def __init__(self, ib_connection_config, log=logtoscreen()):

        # If you copy for another broker include this line
        log.label(broker="IB", clientid = ib_connection_config.client)
        self.__ib_connection_config = ib_connection_config

        # IB specific - this is to ensure we don't get reqID conflicts between different processes
        reqIDoffset = ib_connection_config.client*1000

        #if you copy for another broker, don't forget the logs
        ibServer.__init__(self, log=log)
        ibClient.__init__(self, wrapper = self, reqIDoffset=reqIDoffset, log=log)

        # if you copy for another broker, don't forget to do this
        self.broker_init_error()

        # this is all very IB specific
        self.connect(ib_connection_config.ipaddress, ib_connection_config.portid, ib_connection_config.client)
        thread = Thread(target = self.run)
        thread.start()
        setattr(self, "_thread", thread)

    def __repr__(self):
        return str(self._ib_connection_config)
