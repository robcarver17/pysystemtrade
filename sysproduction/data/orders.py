import datetime
from syscore.objects import (
    arg_not_supplied,
    missing_data,
    no_parent,
    missing_order,
)

from sysdata.mongodb.mongo_order_stack import mongoInstrumentOrderStackData, mongoContractOrderStackData, mongoBrokerOrderStackData
from sysdata.mongodb.mongo_historic_orders import mongoStrategyHistoricOrdersData, mongoContractHistoricOrdersData, mongoBrokerHistoricOrdersData
from sysexecution.fills import listOfFills

from sysdata.data_blob import dataBlob

from sysexecution.order_stacks.broker_order_stack import brokerOrderStackData
from sysexecution.order_stacks.contract_order_stack import contractOrderStackData
from sysexecution.order_stacks.instrument_order_stack import instrumentOrderStackData

from sysexecution.orders.contract_orders import contractOrder
from sysexecution.orders.broker_orders import brokerOrder, brokerOrderWithParentInformation
from sysexecution.orders.instrument_orders import instrumentOrder
from sysexecution.orders.list_of_orders import listOfOrders

from sysobjects.production.tradeable_object import instrumentStrategy, futuresContract


class dataOrders(object):
    def __init__(self, data: dataBlob=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()
        data.add_class_list([mongoInstrumentOrderStackData, mongoContractOrderStackData,
                             mongoBrokerOrderStackData, mongoContractHistoricOrdersData,
                             mongoStrategyHistoricOrdersData, mongoBrokerHistoricOrdersData]
        )
        self._data = data

    @property
    def data(self) -> dataBlob:
        return self._data

    def instrument_stack(self) -> instrumentOrderStackData:
        return self.data.db_instrument_order_stack

    def contract_stack(self) -> contractOrderStackData:
        return self.data.db_contract_order_stack

    def broker_stack(self) -> brokerOrderStackData:
        return self.data.db_broker_order_stack

    def add_historic_orders_to_data(
        self, instrument_order: instrumentOrder,
            list_of_contract_orders: listOfOrders,
            list_of_broker_orders: listOfOrders
    ):
        self.add_historic_instrument_order_to_data(instrument_order)

        for contract_order in list_of_contract_orders:
            self.add_historic_contract_order_to_data(contract_order)

        for broker_order in list_of_broker_orders:
            self.add_historic_broker_order_to_data(broker_order)

    def add_historic_instrument_order_to_data(self, instrument_order: instrumentOrder):
        self.data.db_strategy_historic_orders.add_order_to_data(
            instrument_order)

    def add_historic_contract_order_to_data(self, contract_order: contractOrder):
        self.data.db_contract_historic_orders.add_order_to_data(
            contract_order)

    def add_historic_broker_order_to_data(self, broker_order: brokerOrder):
        self.data.db_broker_historic_orders.add_order_to_data(
            broker_order)

    def get_historic_broker_orders_in_date_range(
        self, period_start: datetime.datetime,
            period_end: datetime.datetime=arg_not_supplied,
    ) -> list:
        # remove split orders
        order_id_list = self.data.db_broker_historic_orders.get_list_of_order_ids_in_date_range(
            period_start, period_end=period_end)


        return order_id_list


    def get_historic_contract_orders_in_date_range(
            self, period_start: datetime.datetime,
            period_end: datetime.datetime) -> list:

        order_id_list = self.data.db_contract_historic_orders.get_list_of_order_ids_in_date_range(
            period_start, period_end
        )

        return order_id_list



    def get_historic_instrument_orders_in_date_range(
            self, period_start: datetime.datetime,
            period_end:datetime.datetime) -> list:
        return self.data.db_strategy_historic_orders.get_list_of_order_ids_in_date_range(
            period_start, period_end
        )

    def get_historic_instrument_order_from_order_id(self, order_id: int) -> instrumentOrder:
        return self.data.db_strategy_historic_orders.get_order_with_orderid(
            order_id)

    def get_historic_contract_order_from_order_id(self, order_id: int) -> contractOrder:
        return self.data.db_contract_historic_orders.get_order_with_orderid(
            order_id)

    def get_historic_broker_order_from_order_id(self, order_id: int) -> brokerOrder:
        return self.data.db_broker_historic_orders.get_order_with_orderid(
            order_id)


    def get_fills_history_for_contract(
        self, futures_contract: futuresContract
    ) -> listOfFills:
        return self.data.db_contract_historic_orders.get_fills_history_for_contract(futures_contract)

    def get_fills_history_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ) -> listOfFills:
        return self.data.db_strategy_historic_orders.get_fills_history_for_instrument_strategy(
            instrument_strategy)


    def get_historic_broker_order_from_order_id_with_execution_data(
            self, order_id: int) -> brokerOrderWithParentInformation:

        # New class?
        # go through each carefully...

        order = self.get_historic_broker_order_from_order_id(order_id)

        contract_order = self.get_parent_contract_order_for_historic_broker_order_id(order_id)
        instrument_order = (
            self.get_parent_instrument_order_for_historic_broker_order_id(order_id))

        augmented_order = brokerOrderWithParentInformation.create_augemented_order(order, contract_order = contract_order,
                                                           instrument_order = instrument_order)

        return augmented_order



    def get_parent_contract_order_for_historic_broker_order_id(self, order_id: int) -> contractOrder:
        broker_order = self.get_historic_broker_order_from_order_id(order_id)
        contract_order_id = broker_order.parent
        if contract_order_id is no_parent:
            return missing_order

        contract_order = self.get_historic_contract_order_from_order_id(
            contract_order_id
        )

        return contract_order

    def get_parent_instrument_order_for_historic_broker_order_id(
            self, order_id: int) -> instrumentOrder:
        contract_order = self.get_parent_contract_order_for_historic_broker_order_id(
            order_id)
        if contract_order is missing_data:
            return missing_order

        instrument_order_id = contract_order.parent
        if instrument_order_id is no_parent:
            return missing_order

        instrument_order = self.get_historic_instrument_order_from_order_id(
            instrument_order_id
        )

        return instrument_order
