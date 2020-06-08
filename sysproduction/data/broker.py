from syscore.objects import missing_data, arg_not_supplied

from sysdata.production.capital import totalCapitalCalculationData
from sysdata.private_config import get_private_then_default_key_value

from sysproduction.data.get_data import dataBlob
from sysproduction.data.currency_data import currencyData


class dataBroker(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_list("ibFxPricesData ibFuturesContractPriceData")
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
        return self.data.broker_futures_contract_price. \
            get_actual_expiry_date_for_instrument_code_and_contract_date(instrument_code, contract_date)

    def get_brokers_instrument_code(self, instrument_code):
        return self.data.broker_futures_contract_price.get_brokers_instrument_code(instrument_code)