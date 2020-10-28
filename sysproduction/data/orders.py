from syscore.objects import (
    arg_not_supplied,
    missing_data,
    no_parent,
    missing_order,
)

from sysdata.mongodb.mongo_order_stack import mongoInstrumentOrderStackData, mongoContractOrderStackData, mongoBrokerOrderStackData
from sysdata.mongodb.mongo_historic_orders import mongoStrategyHistoricOrdersData, mongoContractHistoricOrdersData, mongoBrokerHistoricOrdersData

from sysproduction.data.get_data import dataBlob


class dataOrders(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()
        data.add_class_list([mongoInstrumentOrderStackData, mongoContractOrderStackData,
                             mongoBrokerOrderStackData, mongoContractHistoricOrdersData,
                             mongoStrategyHistoricOrdersData, mongoBrokerHistoricOrdersData]
        )
        self.data = data

    def instrument_stack(self):
        return self.data.db_instrument_order_stack

    def contract_stack(self):
        return self.data.db_contract_order_stack

    def broker_stack(self):
        return self.data.db_broker_order_stack

    def add_historic_orders_to_data(
        self, instrument_order, list_of_contract_orders, list_of_broker_orders
    ):
        self.add_historic_instrument_order_to_data(instrument_order)

        for contract_order in list_of_contract_orders:
            self.add_historic_contract_order_to_data(contract_order)

        for broker_order in list_of_broker_orders:
            self.add_historic_broker_order_to_data(broker_order)

    def add_historic_instrument_order_to_data(self, instrument_order):
        return self.data.db_strategy_historic_orders.add_order_to_data(
            instrument_order)

    def add_historic_contract_order_to_data(self, contract_order):
        return self.data.db_contract_historic_orders.add_order_to_data(
            contract_order)

    def add_historic_broker_order_to_data(self, broker_order):
        return self.data.db_broker_historic_orders.add_order_to_data(
            broker_order)

    def get_historic_broker_orders_in_date_range(
        self, period_start, period_end=arg_not_supplied
    ):
        # remove split orders
        order_id_list = self.data.db_broker_historic_orders.get_orders_in_date_range(
            period_start, period_end=period_end)
        order_id_list = [
            order_id
            for order_id in order_id_list
            if not self.get_historic_broker_order_from_order_id(order_id).is_split_order
        ]
        return order_id_list

    def get_historic_contract_orders_in_date_range(
            self, period_start, period_end):
        return self.data.db_contract_historic_orders.get_orders_in_date_range(
            period_start, period_end
        )

    def get_historic_instrument_orders_in_date_range(
            self, period_start, period_end):
        return self.data.db_strategy_historic_orders.get_orders_in_date_range(
            period_start, period_end
        )

    def get_historic_instrument_order_from_order_id(self, order_id):
        return self.data.db_strategy_historic_orders.get_order_with_orderid(
            order_id)

    def get_historic_contract_order_from_order_id(self, order_id):
        return self.data.db_contract_historic_orders.get_order_with_orderid(
            order_id)

    def get_historic_broker_order_from_order_id(self, order_id):
        return self.data.db_broker_historic_orders.get_order_with_orderid(
            order_id)

    def get_fills_history_for_instrument_and_contract_id(
        self, instrument_code, contract_id
    ):
        return self.data.db_contract_historic_orders.get_fills_history_for_instrument_and_contract_id(
            instrument_code, contract_id)

    def get_fills_history_for_strategy_and_instrument(
        self, strategy_name, instrument_code
    ):
        return self.data.db_strategy_historic_orders.get_fills_history_for_strategy_and_instrument_code(
            strategy_name, instrument_code)

    def get_historic_broker_order_from_order_id_with_execution_data(
            self, order_id):
        order = self.get_historic_broker_order_from_order_id(order_id)
        reference_price = self.get_reference_price_for_historic_broker_order_id(
            order_id)
        generated_datetime = self.get_generated_datetime_for_historic_broker_order_id(
            order_id)
        parent_limit = self.get_parent_limit_for_historic_broker_order_id(
            order_id)

        order.parent_reference_price = reference_price
        order.parent_generated_datetime = generated_datetime
        order.parent_limit_price = parent_limit

        if order.is_split_order:
            # We won't use these, and it may cause bugs for orders saved with
            # legacy data
            calc_mid = None
            calc_side = None
            calc_fill = None
        else:
            calc_mid = order.trade.get_spread_price(order.mid_price)
            calc_side = order.trade.get_spread_price(order.side_price)
            calc_fill = order.trade.get_spread_price(order.filled_price)

        order.calculated_filled_price = calc_fill
        order.calculated_mid_price = calc_mid
        order.calculated_side_price = calc_side

        order.buy_or_sell = order.trade.buy_or_sell()

        return order

    def get_reference_price_for_historic_broker_order_id(self, order_id):
        contract_order = self.get_parent_contract_order_for_historic_broker_order_id(
            order_id)
        if contract_order is missing_order:
            return None

        reference_price = contract_order.reference_price

        return reference_price

    def get_generated_datetime_for_historic_broker_order_id(self, order_id):
        instrument_order = (
            self.get_parent_instrument_order_for_historic_broker_order_id(order_id))
        if instrument_order is missing_order:
            return None

        return instrument_order.generated_datetime

    def get_parent_limit_for_historic_broker_order_id(self, order_id):
        instrument_order = (
            self.get_parent_instrument_order_for_historic_broker_order_id(order_id))
        if instrument_order is missing_order:
            return None

        return instrument_order.limit_price

    def get_parent_contract_order_for_historic_broker_order_id(self, order_id):
        broker_order = self.get_historic_broker_order_from_order_id(order_id)
        contract_order_id = broker_order.parent
        if contract_order_id is no_parent:
            return missing_order

        contract_order = self.get_historic_contract_order_from_order_id(
            contract_order_id
        )

        return contract_order

    def get_parent_instrument_order_for_historic_broker_order_id(
            self, order_id):
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
