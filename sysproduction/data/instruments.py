from sysdata.csv.csv_instrument_data import csvFuturesInstrumentData

from sysdata.data_blob import dataBlob
from sysdata.futures.instruments import futuresInstrumentData
from sysdata.futures.spread_costs import spreadCostData
from sysdata.mongodb.mongo_spread_costs import mongoSpreadCostData
from sysobjects.spot_fx_prices import currencyValue
from sysobjects.instruments import instrumentCosts

from sysproduction.data.currency_data import dataCurrency
from sysproduction.data.generic_production_data import productionDataLayerGeneric


class updateSpreadCosts(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_object(mongoSpreadCostData)
        return data

    def update_spread_costs(self, instrument_code: str, spread_cost: float):
        original_cost = self.db_spread_cost_data.get_spread_cost(instrument_code)
        self.log.msg(
            "Updating spread for %s from %f to %f"
            % (instrument_code, original_cost, spread_cost)
        )
        self.db_spread_cost_data.update_spread_cost(
            instrument_code=instrument_code, spread_cost=spread_cost
        )

    @property
    def db_spread_cost_data(self) -> spreadCostData:
        return self.data.db_spread_cost


class diagInstruments(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data: dataBlob) -> dataBlob:
        data.add_class_list([csvFuturesInstrumentData, mongoSpreadCostData])
        return data

    def get_spread_costs_as_series(self):
        return self.db_spread_cost_data.get_spread_costs_as_series()

    def get_cost_object(self, instrument_code: str) -> instrumentCosts:
        meta_data = self.get_meta_data(instrument_code)
        spread_cost = self.get_spread_cost(instrument_code)

        return instrumentCosts.from_meta_data_and_spread_cost(
            meta_data, spread_cost=spread_cost
        )

    def get_spread_cost(self, instrument_code: str) -> float:
        return self.db_spread_cost_data.get_spread_cost(instrument_code)

    def get_point_size(self, instrument_code: str) -> float:
        return self.get_meta_data(instrument_code).Pointsize

    def get_currency(self, instrument_code: str) -> str:
        return self.get_meta_data(instrument_code).Currency

    def get_point_size_base_currency(self, instrument_code: str) -> float:
        point_size_instrument_currency = self.get_point_size(instrument_code)
        instrument_currency = self.get_currency(instrument_code)

        currency_data = dataCurrency(self.data)
        point_size_currency_value = currencyValue(
            instrument_currency, point_size_instrument_currency
        )
        value = currency_data.currency_value_in_base(point_size_currency_value)

        return value

    def get_asset_class(self, instrument_code: str) -> str:
        return self.get_meta_data(instrument_code).AssetClass

    def get_description(self, instrument_code: str) -> str:
        return self.get_meta_data(instrument_code).Description

    def get_region(self, instrument_code: str) -> str:
        return self.get_meta_data(instrument_code).Region

    def get_meta_data(self, instrument_code: str):
        return self.db_futures_instrument_data.get_instrument_data(
            instrument_code
        ).meta_data

    def get_list_of_instruments(self) -> list:
        return self.db_futures_instrument_data.get_list_of_instruments()

    def get_all_asset_classes(self) -> list:
        instrument_codes = self.get_list_of_instruments()
        list_of_asset_classes = [
            self.get_asset_class(instrument_code)
            for instrument_code in instrument_codes
        ]
        unique_list = list(set(list_of_asset_classes))

        return unique_list

    def get_all_instruments_in_asset_class(self, asset_class: str) -> list:
        instrument_codes = self.get_list_of_instruments()
        instrument_codes = [
            instrument_code
            for instrument_code in instrument_codes
            if self.get_asset_class(instrument_code) == asset_class
        ]

        return instrument_codes

    def get_stale_instruments(self) -> list:
        config = self.data.config
        stale_instruments = config.get_element_or_default("stale_instruments", [])

        return stale_instruments

    @property
    def db_futures_instrument_data(self) -> futuresInstrumentData:
        return self.data.db_futures_instrument

    @property
    def db_spread_cost_data(self) -> spreadCostData:
        return self.data.db_spread_cost


def get_block_size(data, instrument_code):
    diag_instruments = diagInstruments(data)
    return diag_instruments.get_point_size(instrument_code)


def get_stale_instruments(data):
    diag_instruments = diagInstruments(data)
    return diag_instruments.get_stale_instruments()
