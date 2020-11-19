import datetime

from syscore.objects import arg_not_supplied

from sysdata.mongodb.mongo_futures_instruments import mongoFuturesInstrumentData

from sysproduction.data.get_data import dataBlob
from sysproduction.data.currency_data import currencyData
from sysobjects.spot_fx_prices import currencyValue


class diagInstruments(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()

        data.add_class_object(mongoFuturesInstrumentData)
        self.data = data

    def get_point_size(self, instrument_code):
        return self.get_meta_data(instrument_code).Pointsize

    def get_currency(self, instrument_code):
        return self.get_meta_data(instrument_code).Currency

    def get_point_size_base_currency(self, instrument_code):
        point_size_instrument_currency = self.get_point_size(instrument_code)
        instrument_currency = self.get_currency(instrument_code)

        currency_data = currencyData(self.data)
        point_size_currency_value = currencyValue(
            instrument_currency, point_size_instrument_currency
        )
        value = currency_data.currency_value_in_base(point_size_currency_value)

        return value

    def get_asset_class(self, instrument_code):
        return self.get_meta_data(instrument_code).AssetClass

    def get_description(self, instrument_code):
        return self.get_meta_data(instrument_code).Description

    def get_meta_data(self, instrument_code):
        return self.data.db_futures_instrument.get_instrument_data(
            instrument_code
        ).meta_data

    def get_list_of_instruments(self):
        return self.data.db_futures_instrument.get_list_of_instruments()

    def get_all_asset_classes(self):
        instrument_codes = self.get_list_of_instruments()
        list_of_asset_classes = [
            self.get_asset_class(instrument_code)
            for instrument_code in instrument_codes
        ]
        unique_list = list(set(list_of_asset_classes))

        return unique_list

    def get_all_instruments_in_asset_class(self, asset_class):
        instrument_codes = self.get_list_of_instruments()
        instrument_codes = [
            instrument_code
            for instrument_code in instrument_codes
            if self.get_asset_class(instrument_code) == asset_class
        ]

        return instrument_codes
