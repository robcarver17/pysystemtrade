"""

Historic orders

Orders which are still being executed live in the order stack type; see sysexecution

Note orderID here are different from ones used in order stack (which are temporary)

We store three types of orders: strategy level, contract level and broker level

Use to analyse execution and also construct strategy/contract level p&l

Doesn't have to reconcile with positions!

"""
from collections import namedtuple

import pandas as pd

from syscore.objects import arg_not_supplied, missing_order, success, failure

from sysdata.data import baseData
from sysobjects.contracts import futuresContract

from sysexecution.contract_orders import contractTradeableObject

from syslogdiag.log import logtoscreen

Fill = namedtuple("Fill", ["date", "qty", "price"])


def fill_from_order(order):
    if order.fill_equals_zero():
        return missing_order
    fill_price_object = order.filled_price
    fill_datetime = order.fill_datetime
    fill_qty = order.fill

    if fill_price_object is None:
        return missing_order
    if fill_datetime is None:
        return missing_order

    # can't handle spread orders - hopefully should have been resolved now
    assert len(fill_qty) == 1
    fill = fill_qty[0]

    assert len(fill_price_object) == 1
    fill_price = fill_price_object[0]

    return Fill(fill_datetime, fill, fill_price)


class listOfFills(list):
    def __init__(self, list_of_fills):
        list_of_fills = [
            fill for fill in list_of_fills if fill is not missing_order]
        super().__init__(list_of_fills)

    def _as_dict_of_lists(self):
        qty_list = [fill.qty for fill in self]
        price_list = [fill.price for fill in self]
        date_list = [fill.date for fill in self]

        return dict(qty=qty_list, price=price_list, date=date_list)

    def as_pd_df(self):
        self_as_dict = self._as_dict_of_lists()
        date_index = self_as_dict.pop("date")
        df = pd.DataFrame(self_as_dict, index=date_index)
        df = df.sort_index()

        return df


class genericOrdersData(baseData):
    def __init__(self, log=logtoscreen("")):
        self.log = log
        self._dict = {}

    def __repr__(self):
        return "genericOrdersData object"

    def add_order_to_data(self, order):
        order_id = order.order_id
        self._dict[order_id] = order

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
        del self._dict[order_id]
        return success

    def update_order_with_orderid(self, order_id, order):
        self._dict[order_id] = order

    def get_orders_in_date_range(
            start,
            period_start,
            period_end=arg_not_supplied):
        raise NotImplementedError


BASE_CLASS_ERROR = "Need to inherit and override this method"


class strategyHistoricOrdersData(genericOrdersData):
    def get_fills_history_for_strategy_and_instrument_code(
        self, strategy_name, instrument_code
    ):
        """

        :param instrument_code:  str
        :param contract_id: str
        :return: fillHistory object, with fill and price
        """
        order_list = self.get_list_of_orders_for_strategy_and_instrument_code(
            strategy_name, instrument_code
        )
        order_list_as_fills = [fill_from_order(order) for order in order_list]
        list_of_fills = listOfFills(order_list_as_fills)

        return list_of_fills

    def get_list_of_orders_for_strategy_and_instrument_code(
        self, strategy_name, instrument_code
    ):
        list_of_ids = self.get_list_of_order_ids_for_strategy_and_instrument_code(
            strategy_name, instrument_code)
        order_list = []
        for order_id in list_of_ids:
            order = self.get_order_with_orderid(order_id)
            order_list.append(order)

        return order_list

    def get_list_of_order_ids_for_strategy_and_instrument_code(
        self, strategy_name, instrument_code
    ):
        raise NotImplementedError


class contractHistoricOrdersData(genericOrdersData):
    def get_fills_history_for_instrument_and_contract_id(
        self, instrument_code, contract_id
    ):
        """

        :param instrument_code:  str
        :param contract_id: str
        :return: fillHistory object, with fill and price
        """
        order_list = self.get_list_of_orders_for_instrument_and_contract_id(
            instrument_code, contract_id
        )
        order_list_as_fills = [fill_from_order(order) for order in order_list]
        list_of_fills = listOfFills(order_list_as_fills)

        return list_of_fills

    def get_list_of_orders_for_instrument_and_contract_id(
        self, instrument_code, contract_id
    ):
        list_of_ids = self.get_list_of_order_ids_for_instrument_and_contract_id(
            instrument_code, contract_id)
        order_list = []
        for order_id in list_of_ids:
            order = self.get_order_with_orderid(order_id)
            order_list.append(order)

        return order_list

    def get_list_of_order_ids_for_instrument_and_contract_id(
        self, instrument_code, contract_id
    ):
        contract_object = futuresContract(instrument_code, contract_id)

        return self.get_list_of_order_ids_for_contract(contract_object)

    def get_list_of_order_ids_for_contract(self, contract_object):
        list_of_strategies = self.get_list_of_strategies()
        list_of_ids = []
        for strategy_name in list_of_strategies:
            id_list_for_this_strategy = (
                self.get_list_of_order_ids_for_strategy_and_contract(
                    strategy_name, contract_object
                )
            )
            list_of_ids = list_of_ids + id_list_for_this_strategy

        return list_of_ids

    def get_list_of_order_ids_for_strategy_and_contract(
        self, strategy_name, contract_object
    ):
        raise NotImplementedError

    def get_list_of_strategies(self):
        all_keys = self.get_list_of_all_keys()

        def _get_strategy_from_key(key):
            contract_tradeable_object = contractTradeableObject.from_key(key)
            return contract_tradeable_object.strategy_name

        all_strategy_names = [_get_strategy_from_key(key) for key in all_keys]
        unique_strategy_names = list(set(all_strategy_names))

        return unique_strategy_names

    def get_list_of_all_keys(self):
        raise NotImplementedError
