from syscore.objects import arg_not_supplied, missing_data, success, failure

from sysproduction.data.get_data import dataBlob


class diagTrades(object):
    def __init__(self, data = arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()
        data.add_class_list("mongoContractHistoricOrdersData mongoStrategyHistoricOrdersData mongoBrokerHistoricOrdersData")
        self.data = data

    def get_fills_history_for_instrument_and_contract_id(self, instrument_code, contract_id):
        return self.data.db_contract_historic_orders.get_fills_history_for_instrument_and_contract_id(instrument_code, contract_id)

