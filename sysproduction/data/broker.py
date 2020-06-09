from syscore.objects import missing_data, arg_not_supplied

from sysproduction.data.get_data import dataBlob
from sysdata.production.current_positions import contractPosition
from sysproduction.data.positions import diagPositions

class dataBroker(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("ibFxPricesData ibFuturesContractPriceData ibFuturesContractData\
        ibContractPositionData"
                            )
        self.data = data

    def get_fx_prices(self, fx_code):
        return self.data.broker_fx_prices.get_fx_prices(fx_code)

    def get_list_of_fxcodes(self):
        return self.data.broker_fx_prices.get_list_of_fxcodes()

    def get_fx_prices(self, fx_code):
        return self.data.broker_fx_prices.get_fx_prices(fx_code)

    def get_prices_at_frequency_for_contract_object(self, contract_object, frequency):
        return self.data.broker_futures_contract_price.get_prices_at_frequency_for_contract_object(contract_object, frequency)

    def get_actual_expiry_date_for_instrument_code_and_contract_date(self, instrument_code, contract_date):
        return self.data.broker_futures_contract. \
            get_actual_expiry_date_for_instrument_code_and_contract_date(instrument_code, contract_date)

    def get_actual_expiry_date_for_contract(self, contract_object):
        return self.data.broker_futures_contract.get_actual_expiry_date_for_contract(contract_object)

    def get_brokers_instrument_code(self, instrument_code):
        return self.data.broker_futures_contract.get_brokers_instrument_code(instrument_code)

    def get_all_current_contract_positions(self):
        return self.data.broker_contract_position.get_all_current_positions_as_list_with_contract_objects()

    def update_expiries_for_position_list_with_IB_expiries(self, original_position_list):

        for idx in range(len(original_position_list)):
            position_entry = original_position_list[idx]
            actual_expiry = self.get_actual_expiry_date_for_contract(position_entry.contract_object).as_str()
            new_entry = contractPosition(position_entry.position,
                                         position_entry.instrument_code,
                                         actual_expiry)
            original_position_list[idx] = new_entry

        return original_position_list

    def get_list_of_breaks_between_broker_and_db_contract_positions(self):
        diag_positions = diagPositions(self.data)
        db_contract_positions = diag_positions.get_all_current_contract_positions()
        broker_contract_positions = self.get_all_current_contract_positions()

        break_list = db_contract_positions.return_list_of_breaks(broker_contract_positions)

        return break_list