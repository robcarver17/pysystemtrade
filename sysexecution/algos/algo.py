from sysdata.data_blob import dataBlob
from sysexecution.orders.contract_orders import contractOrder
from sysexecution.order_stacks.broker_order_stack import orderWithControls


class Algo(object):
    def __init__(self, data: dataBlob,
                 contract_order: contractOrder):
        self._data = data
        self._contract_order = contract_order

    @property
    def data(self):
        return self._data

    @property
    def contract_order(self):
        return self._contract_order

    def submit_trade(self) -> orderWithControls:
        """

        :return: broker order with control  or missing_order
        """
        raise NotImplementedError

    def manage_trade(self, broker_order_with_controls: orderWithControls) -> orderWithControls:
        """

        :return: broker order with control
        """
        raise NotImplementedError
