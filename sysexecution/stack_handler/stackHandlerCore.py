"""
Stack handler is a giant object, so we split it up into files/classes

This 'core' is inherited by all the other classes and just initialises

"""
from syscore.objects import arg_not_supplied
from sysproduction.data.orders import dataOrders
from sysproduction.data.get_data import dataBlob

class stackHandlerCore(object):
    def __init__(self, data=arg_not_supplied):
        if data is arg_not_supplied:
            data = dataBlob()

        order_data = dataOrders(data)

        instrument_stack = order_data.instrument_stack()
        contract_stack = order_data.contract_stack()
        broker_stack = order_data.broker_stack()

        self.instrument_stack = instrument_stack
        self.contract_stack = contract_stack
        self.broker_stack = broker_stack

        self.order_data = order_data
        self.data = data
        self.log = data.log

