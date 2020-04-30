from syscore.objects import arg_not_supplied

from sysproduction.data.contracts import missing_contract
from sysproduction.data.get_data import dataBlob


class diagState(object):
    def __init__(self, data = arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("mongoRollStateData mongoPositionByContractData")
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
        else:
            position = self.data.mongo_position_by_contract.\
                get_position_for_instrument_and_contract_date(instrument_code, contract_date)

        return position

