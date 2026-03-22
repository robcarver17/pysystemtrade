"""
A-stock instrument configuration and cost model.

Mirrors sysdata/csv/csv_instrument_data.py + csv_spread_costs.py
but for Chinese equities.

Instrument config CSV schema (data/astock/csvconfig/instrumentconfig.csv):
    Instrument,Description,Pointsize,Currency,AssetClass,PerBlock,Percentage,PerTrade,Region

Spread costs CSV schema (data/astock/csvconfig/spreadcosts.csv):
    Instrument,SpreadCost

A股成本说明:
    - 佣金: 万2.5 ~ 万1 (双边), 这里用 Percentage 表示 (如 0.00025)
    - 印花税: 卖出千1 (0.001), 统一计入 PerTrade
    - 滑点: SpreadCost 表示半个价差 (tick_size/2 / price ≈ 0.0005)
    - Pointsize: 股票 = 1 (1元价格变动 = 1元盈亏/每股)
"""

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from syscore.fileutils import resolve_path_and_filename_for_package
from syscore.constants import arg_not_supplied

logger = logging.getLogger(__name__)

ASTOCK_CONFIG_PATH = "data.astock.csvconfig"
INSTRUMENT_CONFIG_FILE = "instrumentconfig.csv"
SPREAD_COSTS_FILE = "spreadcosts.csv"


class AStockInstrumentData:
    """
    A股品种元信息

    兼容 pysystemtrade 的 futuresInstrumentData 接口:
        - get_list_of_instruments() -> list
        - get_instrument_meta_data(code) -> dict
        - get_all_instrument_data_as_df() -> DataFrame
    """

    def __init__(self, datapath: str = arg_not_supplied):
        if datapath is arg_not_supplied:
            datapath = ASTOCK_CONFIG_PATH
        config_file = resolve_path_and_filename_for_package(
            datapath, INSTRUMENT_CONFIG_FILE
        )
        self._config_file = config_file
        self._cache = None

    def __repr__(self):
        return f"AStockInstrumentData @ {self._config_file}"

    def get_list_of_instruments(self) -> List[str]:
        return list(self.get_all_instrument_data_as_df().index)

    def get_all_instrument_data_as_df(self) -> pd.DataFrame:
        if self._cache is not None:
            return self._cache
        try:
            df = pd.read_csv(self._config_file)
            df.index = df["Instrument"]
            df.drop(columns=["Instrument"], inplace=True)
            self._cache = df
            return df
        except Exception as e:
            logger.warning("Cannot read instrument config %s: %s", self._config_file, e)
            return pd.DataFrame()

    def get_instrument_meta_data(self, instrument_code: str) -> dict:
        df = self.get_all_instrument_data_as_df()
        if instrument_code not in df.index:
            return self._default_meta(instrument_code)
        row = df.loc[instrument_code]
        return row.to_dict()

    def get_pointsize(self, instrument_code: str) -> float:
        meta = self.get_instrument_meta_data(instrument_code)
        return float(meta.get("Pointsize", 1.0))

    def get_currency(self, instrument_code: str) -> str:
        meta = self.get_instrument_meta_data(instrument_code)
        return str(meta.get("Currency", "CNY"))

    def get_asset_class(self, instrument_code: str) -> str:
        meta = self.get_instrument_meta_data(instrument_code)
        return str(meta.get("AssetClass", "Equity"))

    @staticmethod
    def _default_meta(instrument_code: str) -> dict:
        return {
            "Description": instrument_code,
            "Pointsize": 1.0,
            "Currency": "CNY",
            "AssetClass": "Equity",
            "PerBlock": 0.0,
            "Percentage": 0.00025,   # 万2.5 佣金
            "PerTrade": 0.001,       # 千1 印花税 (卖出)
            "Region": "CN",
        }


class AStockSpreadCostData:
    """
    A股滑点成本

    SpreadCost = half-spread / price ≈ tick/2/price
    A股最小 tick = 0.01，股价 10 元时 SpreadCost ≈ 0.0005
    """

    def __init__(self, datapath: str = arg_not_supplied):
        if datapath is arg_not_supplied:
            datapath = ASTOCK_CONFIG_PATH
        config_file = resolve_path_and_filename_for_package(
            datapath, SPREAD_COSTS_FILE
        )
        self._config_file = config_file
        self._cache = None

    def __repr__(self):
        return f"AStockSpreadCostData @ {self._config_file}"

    def get_spread_cost(self, instrument_code: str) -> float:
        series = self.get_spread_costs_as_series()
        if instrument_code in series.index:
            return float(series[instrument_code])
        return 0.0005  # 默认半个 tick / 10元股价

    def get_spread_costs_as_series(self) -> pd.Series:
        if self._cache is not None:
            return self._cache
        try:
            df = pd.read_csv(self._config_file)
            df.index = df["Instrument"]
            series = df["SpreadCost"]
            self._cache = series
            return series
        except Exception:
            return pd.Series(dtype=float)

    def get_list_of_instruments(self) -> List[str]:
        return list(self.get_spread_costs_as_series().index)
