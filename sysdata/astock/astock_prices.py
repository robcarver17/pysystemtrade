"""
A-stock price data storage objects.

Provides the same interface pattern as sysdata/csv/csv_adjusted_prices.py
but stores data as Parquet files and works with stock close prices
instead of futures back-adjusted prices.

Data schema  (Parquet / in-memory):
    index : DatetimeIndex  (trade_date, tz-naive, business-day freq)
    columns: price          (float — close price)

File layout:
    data/astock/daily_prices_parquet/<ts_code>.parquet
    data/astock/minutes_prices_parquet/<freq>/<ts_code>.parquet
"""

import os
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── default paths (relative to repo root, dot-separated for resolve_path) ───
DAILY_PRICES_DIRECTORY = "data.astock.daily_prices_parquet"
MINUTES_PRICES_DIRECTORY = "data.astock.minutes_prices_parquet"


def _resolve_parquet_dir(dotpath: str) -> Path:
    """
    将 pysystemtrade 风格的 dot-separated 路径转为绝对目录。
    e.g. 'data.astock.daily_prices_parquet' → <repo>/data/astock/daily_prices_parquet/
    """
    parts = dotpath.split(".")
    # 从本文件往上找到 repo 根（含 setup.py）
    base = Path(__file__).resolve()
    for _ in range(5):
        base = base.parent
        if (base / "setup.py").exists():
            break
    dirpath = base.joinpath(*parts)
    dirpath.mkdir(parents=True, exist_ok=True)
    return dirpath


class AStockDailyPricesData:
    """
    A股日线价格存储

    读写 Parquet 文件，每个品种一个文件。
    index = DatetimeIndex, 列 = ['price']（即 close 价格）

    与 csvFuturesAdjustedPricesData 接口对齐:
        - get_list_of_instruments() -> list[str]
        - get_adjusted_prices(ts_code) -> pd.Series   (名字保留兼容)
        - add_prices(ts_code, pd.Series)
    """

    def __init__(self, datapath: str = DAILY_PRICES_DIRECTORY):
        self._dirpath = _resolve_parquet_dir(datapath)

    def __repr__(self):
        return f"AStockDailyPricesData @ {self._dirpath}"

    # ── read ───────────────────────────────────────────────────

    def get_list_of_instruments(self) -> List[str]:
        return sorted(
            p.stem for p in self._dirpath.glob("*.parquet")
        )

    def get_prices(self, ts_code: str) -> pd.Series:
        """返回 pd.Series, index=DatetimeIndex, values=close price"""
        fpath = self._filepath(ts_code)
        if not fpath.exists():
            return pd.Series(dtype=float)
        df = pd.read_parquet(fpath)
        if "price" not in df.columns:
            return pd.Series(dtype=float)
        s = df["price"]
        s.index = pd.to_datetime(s.index)
        s = s.sort_index()
        s.name = "price"
        return s

    # alias for pysystemtrade compatibility
    get_adjusted_prices = get_prices

    def get_prices_dataframe(self, ts_code: str) -> pd.DataFrame:
        """返回完整 OHLCV DataFrame (如果存储了)"""
        fpath = self._filepath(ts_code)
        if not fpath.exists():
            return pd.DataFrame()
        df = pd.read_parquet(fpath)
        df.index = pd.to_datetime(df.index)
        return df.sort_index()

    # ── write ──────────────────────────────────────────────────

    def add_prices(self, ts_code: str, price_series: pd.Series):
        """写入/覆盖价格"""
        df = pd.DataFrame({"price": price_series})
        df.index.name = "DATETIME"
        fpath = self._filepath(ts_code)
        df.to_parquet(fpath)
        logger.info("Wrote %d rows for %s → %s", len(df), ts_code, fpath)

    def add_ohlcv(self, ts_code: str, ohlcv_df: pd.DataFrame):
        """
        写入完整 OHLCV (保留额外列供分析，price 列 = close).
        ohlcv_df 必须 index = DatetimeIndex, 包含 close 列.
        """
        df = ohlcv_df.copy()
        if "price" not in df.columns and "close" in df.columns:
            df["price"] = df["close"]
        df.index.name = "DATETIME"
        fpath = self._filepath(ts_code)
        df.to_parquet(fpath)
        logger.info("Wrote %d rows (OHLCV) for %s → %s", len(df), ts_code, fpath)

    def append_prices(self, ts_code: str, new_df: pd.DataFrame) -> int:
        """
        增量追加。返回新增行数。
        new_df: index=DatetimeIndex, 至少包含 'price' 列
        """
        existing = self.get_prices_dataframe(ts_code)
        if existing.empty:
            self.add_ohlcv(ts_code, new_df)
            return len(new_df)

        latest = existing.index.max()
        mask = new_df.index > latest
        new_rows = new_df[mask]

        if new_rows.empty:
            return 0

        combined = pd.concat([existing, new_rows])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index()

        if "price" not in combined.columns and "close" in combined.columns:
            combined["price"] = combined["close"]

        combined.index.name = "DATETIME"
        fpath = self._filepath(ts_code)
        combined.to_parquet(fpath)
        logger.info("Appended %d rows for %s (total %d)", len(new_rows), ts_code, len(combined))
        return len(new_rows)

    def get_latest_date(self, ts_code: str) -> Optional[pd.Timestamp]:
        s = self.get_prices(ts_code)
        if s.empty:
            return None
        return s.index.max()

    # ── internal ───────────────────────────────────────────────

    def _filepath(self, ts_code: str) -> Path:
        return self._dirpath / f"{ts_code}.parquet"


class AStockMinutesPricesData:
    """
    A股分钟线价格存储

    文件布局: <base>/<freq>/<ts_code>.parquet
    index = DatetimeIndex (trade_time)
    columns: open, high, low, close, vol, amount, [price]
    """

    def __init__(self, datapath: str = MINUTES_PRICES_DIRECTORY):
        self._basedir = _resolve_parquet_dir(datapath)

    def __repr__(self):
        return f"AStockMinutesPricesData @ {self._basedir}"

    def get_list_of_instruments(self, freq: str = "1min") -> List[str]:
        d = self._basedir / freq
        if not d.exists():
            return []
        return sorted(p.stem for p in d.glob("*.parquet"))

    def get_prices(self, ts_code: str, freq: str = "1min") -> pd.Series:
        fpath = self._filepath(ts_code, freq)
        if not fpath.exists():
            return pd.Series(dtype=float)
        df = pd.read_parquet(fpath)
        col = "price" if "price" in df.columns else "close"
        if col not in df.columns:
            return pd.Series(dtype=float)
        s = df[col]
        s.index = pd.to_datetime(s.index)
        return s.sort_index()

    def get_prices_dataframe(self, ts_code: str, freq: str = "1min") -> pd.DataFrame:
        fpath = self._filepath(ts_code, freq)
        if not fpath.exists():
            return pd.DataFrame()
        df = pd.read_parquet(fpath)
        df.index = pd.to_datetime(df.index)
        return df.sort_index()

    def add_ohlcv(self, ts_code: str, freq: str, ohlcv_df: pd.DataFrame):
        df = ohlcv_df.copy()
        if "price" not in df.columns and "close" in df.columns:
            df["price"] = df["close"]
        df.index.name = "DATETIME"
        fpath = self._filepath(ts_code, freq)
        fpath.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(fpath)
        logger.info("Wrote %d rows (%s) for %s", len(df), freq, ts_code)

    def append_prices(self, ts_code: str, freq: str, new_df: pd.DataFrame) -> int:
        existing = self.get_prices_dataframe(ts_code, freq)
        if existing.empty:
            self.add_ohlcv(ts_code, freq, new_df)
            return len(new_df)

        latest = existing.index.max()
        new_rows = new_df[new_df.index > latest]
        if new_rows.empty:
            return 0

        combined = pd.concat([existing, new_rows])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index()

        if "price" not in combined.columns and "close" in combined.columns:
            combined["price"] = combined["close"]
        combined.index.name = "DATETIME"
        fpath = self._filepath(ts_code, freq)
        combined.to_parquet(fpath)
        logger.info("Appended %d rows (%s) for %s", len(new_rows), freq, ts_code)
        return len(new_rows)

    def get_latest_date(self, ts_code: str, freq: str = "1min") -> Optional[pd.Timestamp]:
        s = self.get_prices(ts_code, freq)
        if s.empty:
            return None
        return s.index.max()

    def _filepath(self, ts_code: str, freq: str) -> Path:
        d = self._basedir / freq
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{ts_code}.parquet"
