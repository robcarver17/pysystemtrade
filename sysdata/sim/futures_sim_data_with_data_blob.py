from sysdata.sim.futures_sim_data import futuresSimData

from sysdata.futures.adjusted_prices import futuresAdjustedPricesData
from sysdata.fx.spotfx import fxPricesData
from sysdata.futures.instruments import futuresInstrumentData
from sysdata.futures.multiple_prices import futuresMultiplePricesData
from sysdata.futures.rolls_parameters import rollParametersData
from sysdata.data_blob import dataBlob


from sysobjects.instruments import (
    assetClassesAndInstruments,
    futuresInstrumentWithMetaData,
)
from sysobjects.spot_fx_prices import fxPrices
from sysobjects.adjusted_prices import futuresAdjustedPrices
from sysobjects.multiple_prices import futuresMultiplePrices
from sysobjects.rolls import rollParameters


class genericBlobUsingFuturesSimData(futuresSimData):
    """
    dataBlob must have the appropriate classes added or it won't work
    """

    def __init__(self, data: dataBlob):
        super().__init__(log=data.log)
        self._data = data

    @property
    def data(self):
        return self._data

    @property
    def db_fx_prices_data(self) -> fxPricesData:
        return self.data.db_fx_prices

    @property
    def db_futures_adjusted_prices_data(self) -> futuresAdjustedPricesData:
        return self.data.db_futures_adjusted_prices

    @property
    def db_futures_instrument_data(self) -> futuresInstrumentData:
        return self.data.db_futures_instrument

    @property
    def db_futures_multiple_prices_data(self) -> futuresMultiplePricesData:
        return self.data.db_futures_multiple_prices

    @property
    def db_roll_parameters(self) -> rollParametersData:
        return self.data.db_roll_parameters

    def get_instrument_list(self):
        return self.db_futures_adjusted_prices_data.get_list_of_instruments()

    def _get_fx_data_from_start_date(
        self, currency1: str, currency2: str, start_date
    ) -> fxPrices:
        fx_code = currency1 + currency2
        data = self.db_fx_prices_data.get_fx_prices(fx_code)

        data_after_start = data[start_date:]

        return data_after_start

    def get_instrument_asset_classes(self) -> assetClassesAndInstruments:
        all_instrument_data = self.get_all_instrument_data_as_df()
        asset_classes = all_instrument_data["AssetClass"]
        asset_class_data = assetClassesAndInstruments.from_pd_series(asset_classes)

        return asset_class_data

    def get_all_instrument_data_as_df(self):
        all_instrument_data = (
            self.db_futures_instrument_data.get_all_instrument_data_as_df()
        )
        instrument_list = self.get_instrument_list()
        all_instrument_data = all_instrument_data[
            all_instrument_data.index.isin(instrument_list)
        ]

        return all_instrument_data

    def get_backadjusted_futures_price(
        self, instrument_code: str
    ) -> futuresAdjustedPrices:
        data = self.db_futures_adjusted_prices_data.get_adjusted_prices(instrument_code)

        return data

    def get_multiple_prices_from_start_date(
        self, instrument_code: str, start_date
    ) -> futuresMultiplePrices:
        data = self.db_futures_multiple_prices_data.get_multiple_prices(instrument_code)

        return data[start_date:]

    def get_instrument_meta_data(
        self, instrument_code: str
    ) -> futuresInstrumentWithMetaData:
        ## cost and other meta data stored in the same place
        return self.get_instrument_object_with_meta_data(instrument_code)

    def get_instrument_object_with_meta_data(
        self, instrument_code: str
    ) -> futuresInstrumentWithMetaData:
        instrument = self.db_futures_instrument_data.get_instrument_data(
            instrument_code
        )

        return instrument

    def get_roll_parameters(self, instrument_code: str) -> rollParameters:
        roll_parameters = self.db_roll_parameters.get_roll_parameters(instrument_code)

        return roll_parameters
