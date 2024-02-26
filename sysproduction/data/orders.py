import datetime
from syscore.constants import arg_not_supplied
from sysexecution.orders.named_order_objects import missing_order, no_parent

from sysdata.production.historic_orders import (
    brokerHistoricOrdersData,
    contractHistoricOrdersData,
    strategyHistoricOrdersData,
)
from sysdata.data_blob import dataBlob

from sysobjects.fills import ListOfFills
from sysexecution.order_stacks.broker_order_stack import brokerOrderStackData
from sysexecution.order_stacks.contract_order_stack import contractOrderStackData
from sysexecution.order_stacks.instrument_order_stack import instrumentOrderStackData

from sysexecution.orders.contract_orders import contractOrder
from sysexecution.orders.broker_orders import (
    brokerOrder,
    brokerOrderWithParentInformation,
)
from sysexecution.orders.instrument_orders import instrumentOrder
from sysexecution.orders.list_of_orders import listOfOrders

from sysobjects.production.tradeable_object import instrumentStrategy, futuresContract

from sysproduction.data.production_data_objects import (
    get_class_for_data_type,
    INSTRUMENT_ORDER_STACK_DATA,
    CONTRACT_ORDER_STACK_DATA,
    BROKER_HISTORIC_ORDERS_DATA,
    STRATEGY_HISTORIC_ORDERS_DATA,
    CONTRACT_HISTORIC_ORDERS_DATA,
    BROKER_ORDER_STACK_DATA,
)


class dataOrders(object):
    def __init__(self, data: dataBlob = arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()
        data.add_class_list(
            [
                get_class_for_data_type(INSTRUMENT_ORDER_STACK_DATA),
                get_class_for_data_type(CONTRACT_ORDER_STACK_DATA),
                get_class_for_data_type(BROKER_ORDER_STACK_DATA),
                get_class_for_data_type(STRATEGY_HISTORIC_ORDERS_DATA),
                get_class_for_data_type(CONTRACT_HISTORIC_ORDERS_DATA),
                get_class_for_data_type(BROKER_HISTORIC_ORDERS_DATA),
            ]
        )
        self._data = data

    @property
    def data(self) -> dataBlob:
        return self._data

    @property
    def db_strategy_historic_orders_data(self) -> strategyHistoricOrdersData:
        return self.data.db_strategy_historic_orders

    @property
    def db_contract_historic_orders_data(self) -> contractHistoricOrdersData:
        return self.data.db_contract_historic_orders

    @property
    def db_broker_historic_orders_data(self) -> brokerHistoricOrdersData:
        return self.data.db_broker_historic_orders

    @property
    def db_instrument_stack_data(self) -> instrumentOrderStackData:
        return self.data.db_instrument_order_stack

    @property
    def db_contract_stack_data(self) -> contractOrderStackData:
        return self.data.db_contract_order_stack

    @property
    def db_broker_stack_data(self) -> brokerOrderStackData:
        return self.data.db_broker_order_stack

    def add_historic_orders_to_data(
        self,
        instrument_order: instrumentOrder,
        list_of_contract_orders: listOfOrders,
        list_of_broker_orders: listOfOrders,
    ):
        self.add_historic_instrument_order_to_data(instrument_order)

        for contract_order in list_of_contract_orders:
            self.add_historic_contract_order_to_data(contract_order)

        for broker_order in list_of_broker_orders:
            self.add_historic_broker_order_to_data(broker_order)

    def add_historic_instrument_order_to_data(self, instrument_order: instrumentOrder):
        self.db_strategy_historic_orders_data.add_order_to_data(instrument_order)

    def add_historic_contract_order_to_data(self, contract_order: contractOrder):
        self.db_contract_historic_orders_data.add_order_to_data(contract_order)

    def add_historic_broker_order_to_data(self, broker_order: brokerOrder):
        self.db_broker_historic_orders_data.add_order_to_data(broker_order)

    def get_historic_broker_order_ids_in_date_range(
        self,
        period_start: datetime.datetime,
        period_end: datetime.datetime = arg_not_supplied,
    ) -> list:
        # remove split orders
        order_id_list = (
            self.db_broker_historic_orders_data.get_list_of_order_ids_in_date_range(
                period_start, period_end=period_end
            )
        )

        return order_id_list

    def get_historic_contract_order_ids_in_date_range(
        self, period_start: datetime.datetime, period_end: datetime.datetime
    ) -> list:
        order_id_list = (
            self.db_contract_historic_orders_data.get_list_of_order_ids_in_date_range(
                period_start, period_end
            )
        )

        return order_id_list

    def get_historic_instrument_order_ids_in_date_range(
        self, period_start: datetime.datetime, period_end: datetime.datetime
    ) -> list:
        order_id_list = (
            self.db_strategy_historic_orders_data.get_list_of_order_ids_in_date_range(
                period_start, period_end
            )
        )

        return order_id_list

    def get_historic_instrument_order_from_order_id(
        self, order_id: int
    ) -> instrumentOrder:
        order = self.db_strategy_historic_orders_data.get_order_with_orderid(order_id)

        return order

    def get_historic_contract_order_from_order_id(self, order_id: int) -> contractOrder:
        order = self.db_contract_historic_orders_data.get_order_with_orderid(order_id)

        return order

    def get_historic_broker_order_from_order_id(self, order_id: int) -> brokerOrder:
        order = self.db_broker_historic_orders_data.get_order_with_orderid(order_id)

        return order

    def get_fills_history_for_contract(
        self, futures_contract: futuresContract
    ) -> ListOfFills:
        ## We get this from broker fills, as they have leg by leg information
        list_of_fills = (
            self.db_broker_historic_orders_data.get_fills_history_for_contract(
                futures_contract
            )
        )

        return list_of_fills

    def get_fills_history_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ) -> ListOfFills:
        list_of_fills = self.db_strategy_historic_orders_data.get_fills_history_for_instrument_strategy(
            instrument_strategy
        )

        return list_of_fills

    def get_historic_broker_order_from_order_id_with_execution_data(
        self, order_id: int
    ) -> brokerOrderWithParentInformation:
        order = self.get_historic_broker_order_from_order_id(order_id)

        contract_order = self.get_parent_contract_order_for_historic_broker_order_id(
            order_id
        )
        instrument_order = (
            self.get_parent_instrument_order_for_historic_broker_order_id(order_id)
        )

        augmented_order = brokerOrderWithParentInformation.create_augmented_order(
            order, contract_order=contract_order, instrument_order=instrument_order
        )

        return augmented_order

    def get_parent_contract_order_for_historic_broker_order_id(
        self, order_id: int
    ) -> contractOrder:
        broker_order = self.get_historic_broker_order_from_order_id(order_id)
        contract_order_id = broker_order.parent
        if contract_order_id is no_parent:
            return missing_order

        contract_order = self.get_historic_contract_order_from_order_id(
            contract_order_id
        )

        return contract_order

    def get_parent_instrument_order_for_historic_broker_order_id(
        self, order_id: int
    ) -> instrumentOrder:
        contract_order = self.get_parent_contract_order_for_historic_broker_order_id(
            order_id
        )
        if contract_order is missing_order:
            return missing_order

        instrument_order_id = contract_order.parent
        if instrument_order_id is no_parent:
            return missing_order

        instrument_order = self.get_historic_instrument_order_from_order_id(
            instrument_order_id
        )

        return instrument_order
