"""

Historic orders

Orders which are still being executed live in the order stack type; see sysexecution

Note orderID here are different from ones used in order stack (which are temporary)

We store three types of orders: strategy level, contract level and broker level

Use to analyse execution and also construct strategy/contract level p&l

Doesn't have to reconcile with positions!

"""
from collections import namedtuple
import datetime

import pandas as pd

from syscore.objects import arg_not_supplied, missing_order, success, failure

from sysdata.base_data import baseData
from sysexecution.orders.base_orders import Order
from sysexecution.order_stacks.order_stack import missingOrder
from sysexecution.orders.list_of_orders import listOfOrders

from sysobjects.contracts import futuresContract

from sysobjects.production.tradeable_object import futuresContractStrategy, instrumentStrategy, futuresContract

from syslogdiag.log import logtoscreen

Fill = namedtuple("Fill", ["date", "qty", "price"])



class listOfFills(list):
    def __init__(self, list_of_fills):
        list_of_fills = [
            fill for fill in list_of_fills if fill is not missing_order]
        super().__init__(list_of_fills)

    @classmethod
    def from_list_of_orders(listOfFills, list_of_orders: listOfOrders):
        order_list_as_fills = [fill_from_order(order) for order in list_of_orders]
        list_of_fills = listOfFills(order_list_as_fills)

        return list_of_fills

    def _as_dict_of_lists(self) -> dict:
        qty_list = [fill.qty for fill in self]
        price_list = [fill.price for fill in self]
        date_list = [fill.date for fill in self]

        return dict(qty=qty_list, price=price_list, date=date_list)

    def as_pd_df(self) -> pd.DataFrame:
        self_as_dict = self._as_dict_of_lists()
        date_index = self_as_dict.pop("date")
        df = pd.DataFrame(self_as_dict, index=date_index)
        df = df.sort_index()

        return df


def fill_from_order(order: Order) -> Fill:
    if order.fill_equals_zero():
        return missing_order

    fill_price = order.filled_price
    fill_datetime = order.fill_datetime
    fill_qty = order.fill

    if fill_price.is_empty():
        return missing_order

    if fill_datetime is None:
        return missing_order

    return Fill(fill_datetime, fill_qty, fill_price)


class genericOrdersData(baseData):
    def __init__(self, log=logtoscreen("")):
        super().__init__(log=log)

    def __repr__(self):
        return "genericOrdersData object"


    def delete_order_with_orderid(self, order_id: int):
        order = self.get_order_with_orderid(order_id)
        if order is missing_order:
            raise missingOrder
        self._delete_order_with_orderid_without_checking(order_id)

    def add_order_to_data(self, order: Order, ignore_duplication=False):
        raise NotImplementedError

    def get_list_of_order_ids(self) -> list:
        raise NotImplementedError

    def get_order_with_orderid(self, order_id: int):
        # return missing_order if not found
        raise NotImplementedError


    def _delete_order_with_orderid_without_checking(self, order_id: int):
        raise NotImplementedError

    def update_order_with_orderid(self, order_id: int, order: Order):
        raise NotImplementedError

    def get_list_of_order_ids_in_date_range(
            self,
            period_start: datetime.datetime,
            period_end: datetime.datetime=arg_not_supplied) -> list:

        raise NotImplementedError




class strategyHistoricOrdersData(genericOrdersData):
    def get_fills_history_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ) -> listOfFills:
        """

        :param instrument_code:  str
        :param contract_id: str
        :return: fillHistory object, with fill and price
        """
        order_list = self.get_list_of_orders_for_instrument_strategy(
            instrument_strategy
        )
        order_list_as_fills = [fill_from_order(order) for order in order_list]
        list_of_fills = listOfFills(order_list_as_fills)

        return list_of_fills

    def get_list_of_orders_for_instrument_strategy(self, instrument_strategy: instrumentStrategy) -> listOfOrders:
        list_of_ids = self.get_list_of_order_ids_for_instrument_strategy(instrument_strategy)
        order_list = []
        for order_id in list_of_ids:
            order = self.get_order_with_orderid(order_id)
            order_list.append(order)

        order_list = listOfOrders(order_list)

        return order_list

    def get_list_of_order_ids_for_instrument_strategy(self, instrument_strategy: instrumentStrategy):

        raise NotImplementedError


class contractHistoricOrdersData(genericOrdersData):
    def get_fills_history_for_contract(
        self, futures_contract: futuresContract
    ) -> listOfFills:
        """

        :param instrument_code:  str
        :param contract_id: str
        :return: fillHistory object, with fill and price
        """
        list_of_orders = self.get_list_of_orders_for_contract(futures_contract)
        list_of_fills = listOfFills.from_list_of_orders(list_of_orders)

        return list_of_fills

    def get_list_of_orders_for_contract(
        self, futures_contract: futuresContract
    ) -> listOfOrders:

        list_of_ids = self.get_list_of_order_ids_for_contract(
            futures_contract)
        order_list = []
        for order_id in list_of_ids:
            order = self.get_order_with_orderid(order_id)
            order_list.append(order)

        order_list = listOfOrders(order_list)

        return order_list


    def get_list_of_order_ids_for_contract(self, futures_contract: futuresContract) -> list:
        list_of_strategies = self.get_list_of_strategies()
        list_of_ids = []
        for strategy_name in list_of_strategies:
            futures_contract_strategy = \
                futuresContractStrategy.from_strategy_name_and_contract_object(strategy_name=strategy_name,
                                                                           futures_contract=futures_contract)
            id_list_for_this_strategy = (
                self.get_list_of_order_ids_for_strategy_and_contract(
                    futures_contract_strategy
                )
            )
            list_of_ids = list_of_ids + id_list_for_this_strategy

        return list_of_ids


    def get_list_of_strategies(self):
        raise NotImplementedError

    def get_list_of_order_ids_for_strategy_and_contract(
        self, futures_contract_strategy: futuresContractStrategy
    ):
        raise NotImplementedError

class brokerHistoricOrdersData(contractHistoricOrdersData):
    pass
