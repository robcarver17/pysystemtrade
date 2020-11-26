from sysdata.sim.futures_sim_data import futuresSimData

from sysdata.data_blob import dataBlob

from sysobjects.instruments import assetClassesAndInstruments,  futuresInstrumentWithMetaData
from sysobjects.spot_fx_prices import fxPrices
from sysobjects.adjusted_prices import futuresAdjustedPrices
from sysobjects.multiple_prices import futuresMultiplePrices

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

    def get_instrument_list(self):
        return self.data.db_futures_adjusted_prices.get_list_of_instruments()

    def _get_fx_data(self, currency1: str, currency2: str) -> fxPrices:
        fx_code = currency1+currency2
        data = self.data.db_fx_prices.get_fx_prices(fx_code)

        return data

    def get_instrument_asset_classes(self) -> assetClassesAndInstruments:
        all_instrument_data = self.data.db_futures_instrument.get_all_instrument_data_as_df()
        asset_classes = all_instrument_data['AssetClass']
        asset_class_data = assetClassesAndInstruments.from_pd_series(asset_classes)

        return asset_class_data

    def get_backadjusted_futures_price(self, instrument_code: str) -> futuresAdjustedPrices:
        data = self.data.db_futures_adjusted_prices.get_adjusted_prices(instrument_code)

        return data

    def get_multiple_prices(self, instrument_code: str) -> futuresMultiplePrices:
        data = self.data.db_futures_multiple_prices.get_multiple_prices(instrument_code)

        return data

    def _get_instrument_object_with_cost_data(self, instrument_code: str) -> futuresInstrumentWithMetaData:
        ## cost and other meta data stored in the same place
        return self._get_instrument_object_with_meta_data(instrument_code)

    def _get_instrument_object_with_meta_data(self, instrument_code: str) -> futuresInstrumentWithMetaData:
        instrument = self.data.db_futures_instrument.get_instrument_data(instrument_code)

        return instrument


