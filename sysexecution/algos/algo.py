from syscore.objects import missing_order


class Algo(object):
    def __init__(self, data, contract_order):
        self._data = data
        self._contract_order = contract_order

    @property
    def data(self):
        return self._data

    @property
    def contract_order(self):
        return self._contract_order

    def submit_trade(self):
        """

        :return: broker order with control  or missing_order
        """
        raise NotImplementedError

    def manage_trade(self, broker_order_with_controls):
        """

        :return: broker order with control
        """
        raise NotImplementedError
