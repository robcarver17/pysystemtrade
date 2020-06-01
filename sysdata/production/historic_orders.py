"""

Historic orders

Orders which are still being executed live in the order stack type; see sysexecution

Note orderID here are different from ones used in order stack (which are temporary)

We store two types of orders: strategy level and contract level

Use to analyse execution and also construct strategy/contract level p&l

Doesn't have to reconcile with positions!

"""
import datetime
from syscore.objects import arg_not_supplied, missing_order, success, failure
from syscore.genutils import  none_to_object, object_to_none
from sysdata.data import baseData

from syslogdiag.log import logtoscreen

class historicStrategyOrder(object):
    def __init__(self, strategy_name="", instrument_code="", quantity_filled=0, filled_price=arg_not_supplied,
                 order_id=arg_not_supplied,
                 fill_datetime=arg_not_supplied):
        self.strategy_name = strategy_name
        self.instrument_code = instrument_code
        self.quantity_filled = quantity_filled
        self.filled_price = none_to_object(filled_price, arg_not_supplied)
        self.order_id = none_to_object(order_id, arg_not_supplied)
        self.fill_datetime = none_to_object(fill_datetime, arg_not_supplied)

    def __repr__(self):
        return str(self.as_dict())

    def as_dict(self):
        return dict(strategy_name = self.strategy_name,
                    instrument_code = self.instrument_code,
                    quantity_filled = self.quantity_filled,
                    filled_price = object_to_none(self.filled_price,arg_not_supplied),
                    order_id = object_to_none(self.order_id,arg_not_supplied),
                 fill_datetime = object_to_none(self.fill_datetime, arg_not_supplied))

    @classmethod
    def from_dict(historicStrategyOrder, kwargs):
        return historicStrategyOrder(**kwargs)

def from_instrument_and_contract_orders_to_historic_orders(instrument_order, list_of_contract_orders):
    """
    Goes from a list of filled orders on order stacks to objects for permanent historic order storage

    :param instrument_order: from order stack
    :param list_of_contract_orders: from order stack
    :return: tuple: historicStrategyOrder and list of historicInstrumentOrders
    """

    pass

class historicContractOrder(object):

    def __init__(self, strategy_name="", instrument_code="", contract_id="", quantity_filled=0,
                 filled_price=arg_not_supplied, order_id=arg_not_supplied,
                 order_type="best",
                 limit_price = arg_not_supplied, reference_price = arg_not_supplied, side_price = arg_not_supplied,
                 offside_price = arg_not_supplied,
                 linked_instrument_order = arg_not_supplied, algo_used = "",
                 algo_state="",
                 broker = "", broker_account = "", broker_clientid = "",
                 commission = 0.0,
                 reference_datetime= arg_not_supplied, submit_datetime = arg_not_supplied, fill_datetime = arg_not_supplied,
                 broker_permid = "", broker_tempid = "",
                 manual_fill = False,
                 manual_trade = False,
                 roll_order = False,
                 inter_spread_order = False,
                 calendar_spread_order = False,
                 linked_spread_orders = [],

                 comment = ""
                 ):
        self.strategy_name = strategy_name
        self.instrument_code = instrument_code
        self.contract_id = contract_id

        self.quantity_filled = quantity_filled
        self.filled_price = none_to_object(filled_price, arg_not_supplied)
        self.order_id = none_to_object(order_id, arg_not_supplied)

        self.order_type = order_type#
        self.limit_price = none_to_object(limit_price, arg_not_supplied)
        self.reference_price = none_to_object(reference_price, arg_not_supplied)
        self.side_price = none_to_object(side_price, arg_not_supplied)
        self.offside_price = none_to_object(offside_price, arg_not_supplied)

        self.linked_instrument_order = none_to_object(linked_instrument_order, arg_not_supplied)
        self.algo_used = algo_used
        self.algo_state = algo_state

        self.broker = broker
        self.broker_account = broker_account
        self.broker_clientid = broker_clientid
        self.broker_tempid = broker_tempid
        self.broker_permid = broker_permid
        self.commission = commission #

        self.reference_datetime = none_to_object(reference_datetime, arg_not_supplied)
        self.submit_datetime = none_to_object(submit_datetime, arg_not_supplied)
        self.fill_datetime = none_to_object(fill_datetime, arg_not_supplied)

        self.manual_fill = manual_fill #
        self.manual_trade = manual_trade #
        self.inter_spread_order = inter_spread_order#
        self.calendar_spread_order = calendar_spread_order#
        self.roll_order = roll_order#

        self.comment = comment#
        self.linked_spread_orders = linked_spread_orders#

    def __repr__(self):
        return str(self.as_dict())

    def as_dict(self):
        return dict(
        strategy_name = self.strategy_name,
        instrument_code = self.instrument_code,
        contract_id = self.contract_id,

        quantity_filled = self.quantity_filled,
        filled_price = object_to_none(self.filled_price,arg_not_supplied),
        order_id = object_to_none(self.order_id,arg_not_supplied),

        order_type = self.order_type,
        limit_price = object_to_none(self.limit_price, arg_not_supplied),
        reference_price = object_to_none(self.reference_price, arg_not_supplied),
        side_price = object_to_none(self.side_price, arg_not_supplied),
        offside_price = object_to_none(self.offside_price, arg_not_supplied),

        linked_instrument_order = object_to_none(self.linked_instrument_order, arg_not_supplied),
        algo_used = self.algo_used,
        algo_state = self.algo_state,

        broker = self.broker,
        broker_account = self.broker_account,
        broker_clientid = self.broker_clientid,
        broker_tempid = self.broker_tempid,
        broker_permid = self.broker_permid,
        commission = self.commission,

        reference_datetime = object_to_none(self.reference_datetime, arg_not_supplied),
        submit_datetime = object_to_none(self.submit_datetime, arg_not_supplied),
        fill_datetime = object_to_none(self.fill_datetime, arg_not_supplied),

        manual_fill = self.manual_fill,
        manual_trade = self.manual_trade,
        inter_spread_order = self.inter_spread_order,
        calendar_spread_order = self.calendar_spread_order,
        roll_order = self.roll_order,

        comment = self.comment,
        linked_spread_orders = self.linked_spread_orders)


    @classmethod
    def from_dict(historicContractOrder, kwargs):
        return historicContractOrder(**kwargs)


class genericOrdersData(baseData):
    def __init__(self, log = logtoscreen("")):
        self.log = log
        self._dict = {}
        self._orderid = 0

    def __repr__(self):
        return "genericOrdersData object"

    def add_order_to_data(self, order):
        order_id = self.get_next_order_id()
        self._dict [ order_id] = order

        return order_id

    def get_list_of_order_ids(self):
        return self._dict.keys()

    def _get_next_order_id(self):
        current_orderid = self._orderid
        new_orderid = current_orderid + 1
        self._orderid = new_orderid
        return new_orderid

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

