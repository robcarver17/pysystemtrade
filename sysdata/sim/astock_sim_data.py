"""
AStockSimData - pysystemtrade simData implementation for Chinese equities.

Inheritance chain (mirrors futures pattern):
    baseData → simData → AStockSimData

This class reads from local Parquet stores (populated by the fetcher)
and exposes the interface that pysystemtrade's System/stages expect:

Required by simData base:
    - get_instrument_list()
    - get_raw_price_from_start_date(code, start)
    - get_instrument_currency(code)
    - get_value_of_block_price_move(code)
    - get_raw_cost_data(code)
    - _get_fx_data_from_start_date(c1, c2, start)

Additional for A-stock analysis:
    - get_ohlcv(code)
    - get_minutes_prices(code, freq)

Usage:
    from sysdata.sim.astock_sim_data import AStockSimData
    data = AStockSimData()
    system = System([...stages...], data=data, config=config)
"""

import datetime
import pandas as pd

from syscore.exceptions import missingData
from sysdata.sim.sim_data import simData
from sysdata.astock.astock_prices import AStockDailyPricesData, AStockMinutesPricesData
from sysdata.astock.astock_instruments import AStockInstrumentData, AStockSpreadCostData

from sysobjects.spot_fx_prices import fxPrices
from sysobjects.instruments import instrumentCosts
from syslogging.logger import *


class AStockSimData(simData):
    """
    simData for A-stock backtesting.

    Reads daily close prices from Parquet files, provides instrument
    metadata and cost data, and returns CNY/CNY = 1.0 for FX.
    """

    def __init__(
        self,
        daily_prices_path: str = None,
        minutes_prices_path: str = None,
        instrument_config_path: str = None,
        log=get_logger("AStockSimData"),
    ):
        super().__init__(log=log)

        # Data stores
        if daily_prices_path:
            self._daily_store = AStockDailyPricesData(datapath=daily_prices_path)
        else:
            self._daily_store = AStockDailyPricesData()

        if minutes_prices_path:
            self._minutes_store = AStockMinutesPricesData(datapath=minutes_prices_path)
        else:
            self._minutes_store = AStockMinutesPricesData()

        if instrument_config_path:
            self._instrument_data = AStockInstrumentData(datapath=instrument_config_path)
            self._spread_cost_data = AStockSpreadCostData(datapath=instrument_config_path)
        else:
            self._instrument_data = AStockInstrumentData()
            self._spread_cost_data = AStockSpreadCostData()

    def __repr__(self):
        n = len(self.get_instrument_list())
        return f"AStockSimData with {n} instruments"

    # ── simData required interface ─────────────────────────────

    def get_instrument_list(self) -> list:
        """List of A-stock instruments available in daily price store."""
        return self._daily_store.get_list_of_instruments()

    def get_raw_price_from_start_date(
        self, instrument_code: str, start_date: datetime.datetime
    ) -> pd.Series:
        """
        Returns close price series from start_date onwards.

        This is the core method that simData.get_raw_price() calls,
        and that daily_prices() resamples to business-day index.
        """
        prices = self._daily_store.get_prices(instrument_code)
        if prices.empty:
            return prices
        return prices[start_date:]

    def get_instrument_currency(self, instrument_code: str) -> str:
        """All A-stocks are priced in CNY."""
        return self._instrument_data.get_currency(instrument_code)

    def get_value_of_block_price_move(self, instrument_code: str) -> float:
        """
        For stocks, a ¥1 move per share = ¥1 value change per share.
        Pointsize = 1.0 for equities.
        """
        return self._instrument_data.get_pointsize(instrument_code)

    def get_raw_cost_data(self, instrument_code: str) -> instrumentCosts:
        """
        A-stock cost model:
          - Percentage commission: ~万2.5 (0.025%) each way
          - PerTrade: 印花税 千1 (0.1%) on sell
          - SpreadCost: half-tick / price ≈ 0.0005
        """
        meta = self._instrument_data.get_instrument_meta_data(instrument_code)
        spread_cost = self._spread_cost_data.get_spread_cost(instrument_code)

        return instrumentCosts(
            price_slippage=spread_cost,
            value_of_block_commission=meta.get("PerBlock", 0.0),
            percentage_cost=meta.get("Percentage", 0.00025),
            value_of_pertrade_commission=meta.get("PerTrade", 0.001),
        )

    def _get_fx_data_from_start_date(
        self, currency1: str, currency2: str, start_date: datetime.datetime
    ) -> fxPrices:
        """
        FX data for A-stocks.

        Since everything is CNY-denominated and we backtest in CNY,
        return a constant 1.0 series. If someone needs CNYUSD etc,
        this can be extended later.
        """
        if currency1 == currency2:
            return _constant_fx_series(start_date)

        # CNY base — return 1.0
        return _constant_fx_series(start_date)

    # ── futures-compat stubs (让 RawData 等 stage 优雅回退) ────

    def get_instrument_raw_carry_data(self, instrument_code: str):
        """A-stocks have no carry data — raise missingData so RawData falls back."""
        raise missingData(
            "No carry data for A-stock %s (equities don't have carry)"
            % instrument_code
        )

    def get_backadjusted_futures_price(self, instrument_code: str):
        raise missingData("A-stocks are not futures — no back-adjusted price")

    def get_multiple_prices_from_start_date(self, instrument_code: str, start_date):
        raise missingData("A-stocks are not futures — no multiple prices")

    def get_instrument_asset_classes(self):
        """Return asset class mapping compatible with pysystemtrade."""
        from sysobjects.instruments import assetClassesAndInstruments
        instruments = self.get_instrument_list()
        mapping = {code: self._instrument_data.get_asset_class(code) for code in instruments}
        series = pd.Series(mapping)
        return assetClassesAndInstruments.from_pd_series(series)

    # ── extended A-stock methods ───────────────────────────────

    def get_ohlcv(self, instrument_code: str) -> pd.DataFrame:
        """Get full OHLCV daily data (if stored)."""
        return self._daily_store.get_prices_dataframe(instrument_code)

    def get_minutes_prices(
        self, instrument_code: str, freq: str = "1min"
    ) -> pd.Series:
        """Get intraday close prices at given frequency."""
        return self._minutes_store.get_prices(instrument_code, freq)

    def get_minutes_ohlcv(
        self, instrument_code: str, freq: str = "1min"
    ) -> pd.DataFrame:
        """Get full intraday OHLCV data."""
        return self._minutes_store.get_prices_dataframe(instrument_code, freq)

    def get_instrument_asset_class(self, instrument_code: str) -> str:
        return self._instrument_data.get_asset_class(instrument_code)

    # ── properties for direct access ───────────────────────────

    @property
    def daily_store(self) -> AStockDailyPricesData:
        return self._daily_store

    @property
    def minutes_store(self) -> AStockMinutesPricesData:
        return self._minutes_store


def _constant_fx_series(
    start_date: datetime.datetime,
    end_date: datetime.datetime = None,
) -> fxPrices:
    """Return a constant 1.0 FX series from start to ~today."""
    if end_date is None:
        end_date = datetime.datetime.now()
    dates = pd.bdate_range(start=start_date, end=end_date)
    series = pd.Series(1.0, index=dates)
    return fxPrices(series)
