from syscore.objects import arg_not_supplied, missing_data, success, failure

from sysproduction.data.get_data import dataBlob


class dataOrders(object):
    def __init__(self, data = arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()
        data.add_class_list("mongoInstrumentOrderStackData mongoContractOrderStackData mongoBrokerOrderStackData")
        data.add_class_list("mongoContractHistoricOrdersData mongoStrategyHistoricOrdersData mongoBrokerHistoricOrdersData")
        self.data = data

    def instrument_stack(self):
        return self.data.db_instrument_order_stack

    def contract_stack(self):
        return self.data.db_contract_order_stack

    def broker_stack(self):
        return self.data.db_broker_order_stack

    def add_historic_orders_to_data(self, instrument_order, list_of_contract_orders, list_of_broker_orders):
        self.add_historic_instrument_order_to_data(instrument_order)

        for contract_order in list_of_contract_orders:
            self.add_historic_contract_order_to_data(contract_order)

        for broker_order in list_of_broker_orders:
            self.add_historic_broker_order_to_data(broker_order)


    def add_historic_instrument_order_to_data(self, instrument_order):
        return self.data.db_strategy_historic_orders.add_order_to_data(instrument_order)

    def add_historic_contract_order_to_data(self, contract_order):
        return self.data.db_contract_historic_orders.add_order_to_data(contract_order)

    def add_historic_broker_order_to_data(self, broker_order):
        return self.data.db_broker_historic_orders.add_order_to_data(broker_order)


