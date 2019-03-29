"""
Classes to create instances of connections

Connections contain plugs to data and brokers, so the two can talk to each other
"""

import yaml
from threading import Thread

from sysbrokers.IB.ibClient import ibClient
from sysbrokers.IB.ibServer import ibServer
from syslogdiag.log import logtoscreen

from syscore.fileutils import get_filename_for_package

PRIVATE_CONFIG_FILE = get_filename_for_package("private.private_config.yaml")

DEFAULT_IB_IPADDRESS='127.0.0.1'
DEFAULT_IB_PORT = 4001

def ib_defaults(config_file =PRIVATE_CONFIG_FILE, **kwargs):
    """
    Returns ib configuration with following precedence

    1- if passed in arguments: ipaddress, port - use that
    2- if defined in private_config file, use that. ib_ipaddress, ib_port
    3- otherwise use defaults DEFAULT_MONGO_DB, DEFAULT_MONGO_HOST, DEFAULT_MONGOT_PORT

    :return: mongo db, hostname, port
    """

    try:
        with open(config_file) as file_to_parse:
            yaml_dict = yaml.load(file_to_parse)
    except:
        yaml_dict={}

    # Overwrite with passed arguments - these will take precedence over values in config file
    for arg_name in ['ipaddress', 'port']:
        arg_value = kwargs.get(arg_name, None)
        if arg_value is not None:
            yaml_dict['ib_'+arg_name] = arg_value

    # Get from dictionary
    ipaddress = yaml_dict.get('ib_ipaddress', DEFAULT_IB_IPADDRESS)
    port = yaml_dict.get('ib_port', DEFAULT_IB_PORT)

    return ipaddress, port



class connectionIB(ibClient, ibServer):
    """
    Connection object for connecting IB
    (A database plug in will need to be added for streaming prices)
    """

    def __init__(self, client=1, ipaddress=None, port=None, log=logtoscreen()):

        # resolve defaults
        ipaddress, port = ib_defaults(ipaddress=ipaddress, port=port)

        # If you copy for another broker include this line
        log.label(broker="IB", clientid = client)
        self._ib_connection_config = dict(ipaddress = ipaddress, port = port, client = client)

        # IB specific - this is to ensure we don't get reqID conflicts between different processes
        reqIDoffset = client*1000

        #if you copy for another broker, don't forget the logs
        ibServer.__init__(self, log=log)
        ibClient.__init__(self, wrapper = self, reqIDoffset=reqIDoffset, log=log)

        # if you copy for another broker, don't forget to do this
        self.broker_init_error()

        # this is all very IB specific
        self.connect(ipaddress, port, client)
        thread = Thread(target = self.run)
        thread.start()
        setattr(self, "_thread", thread)

    def __repr__(self):
        return "IB broker connection"+str(self._ib_connection_config)
