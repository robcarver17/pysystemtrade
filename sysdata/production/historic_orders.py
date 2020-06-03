"""

Historic orders

Orders which are still being executed live in the order stack type; see sysexecution

Note orderID here are different from ones used in order stack (which are temporary)

We store three types of orders: strategy level, contract level and broker level

Use to analyse execution and also construct strategy/contract level p&l

Doesn't have to reconcile with positions!

"""
import datetime
from syscore.objects import arg_not_supplied, missing_order, success, failure
from syscore.genutils import  none_to_object, object_to_none
from sysdata.data import baseData

from syslogdiag.log import logtoscreen


class genericOrdersData(baseData):
    def __init__(self, log = logtoscreen("")):
        self.log = log
        self._dict = {}

    def __repr__(self):
        return "genericOrdersData object"

    def add_order_to_data(self, order):
        order_id = order.order_id
        self._dict [ order_id] = order

        return order_id

    def get_list_of_order_ids(self):
        return self._dict.keys()

    def get_order_with_orderid(self, order_id):
        order = self._dict.get(order_id, missing_order)
        return order

    def delete_order_with_orderid(self, order_id):
        order = self.get_order_with_orderid(order_id)
        if order is missing_order:
            return failure
        del(self._dict[order_id])
        return success

    def update_order_with_orderid(self, order_id, order):
        self._dict[order_id] = order




BASE_CLASS_ERROR = "Need to inherit and override this method"

class strategyHistoricOrdersData(genericOrdersData):
    def get_list_of_orders_for_strategy(self, strategy_name):
        raise NotImplementedError(BASE_CLASS_ERROR)

    def get_list_of_orders_for_strategy_and_instrument(self, strategy_name, instrument_code):
        raise NotImplementedError(BASE_CLASS_ERROR)

class contractHistoricOrdersData(genericOrdersData):
    def get_list_of_recent_orders(self, recent_days=1):
        now = datetime.datetime.now()
        recent_datetime = now + datetime.timedelta(days=recent_days)

        return self.get_list_of_orders_since_date(recent_datetime)

    def get_list_of_orders_since_date(self, recent_datetime):
        raise NotImplementedError

