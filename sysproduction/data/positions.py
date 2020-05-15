from syscore.objects import arg_not_supplied, missing_data

from sysproduction.data.contracts import missing_contract
from sysproduction.data.get_data import dataBlob


class diagPositions(object):
    def __init__(self, data = arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("mongoRollStateData mongoContractPositionData mongoStrategyPositionData")
        self.data = data

    def get_roll_state(self, instrument_code):
        return self.data.mongo_roll_state.get_roll_state(instrument_code)

    def get_positions_for_instrument_and_contract_list(self, instrument_code, contract_list):
        list_of_positions = [self.get_position_for_instrument_and_contract_date(instrument_code, contract_date)
                             for contract_date in contract_list]

        return list_of_positions

    def get_position_for_instrument_and_contract_date(self, instrument_code, contract_date):
        if contract_date is missing_contract:
            return 0.0
        position = self.data.mongo_contract_position.\
                get_current_position_for_instrument_and_contract_date(instrument_code, contract_date)
        if position is missing_data:
            return 0.0

        return position.position

    def get_position_for_strategy_and_instrument(self, strategy_name, instrument_code):
        position = self.data.mongo_strategy_position.get_current_position_for_strategy_and_instrument(strategy_name, instrument_code)
        if position is missing_data:
            return 0.0
        return position.position

    def get_list_of_instruments_for_strategy_with_position(self, strategy_name):
        instrument_list = self.data.mongo_strategy_position.get_list_of_instruments_for_strategy_with_position(strategy_name)
        return instrument_list


