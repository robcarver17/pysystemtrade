"""
A-Stock PostgreSQL 存储后端

提供与 Parquet 版本完全相同的接口，可透明替换。
所有类均接受 SQLAlchemy Engine 参数。

Tables:
    astock_daily_prices    — 日线 OHLCV
    astock_minute_prices   — 分钟线 OHLCV (按 freq 分区)
    astock_instruments     — 品种元信息
    astock_spread_costs    — 滑点成本
    astock_valid_symbols   — 已验证有效品种

使用 TimescaleDB 友好的 schema (如果安装了 timescale 扩展可进一步优化)。
"""

import logging
from datetime import datetime
from typing import List, Optional

import pandas as pd
from sqlalchemy import (
    MetaData, Table, Column, String, Float, DateTime, Integer,
    BigInteger, UniqueConstraint, Index, text,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

logger = logging.getLogger(__name__)

# ── Schema 定义 ──────────────────────────────────────────────────

metadata = MetaData()

t_daily_prices = Table(
    "astock_daily_prices", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("ts_code", String(20), nullable=False),
    Column("dt", DateTime, nullable=False),
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float),
    Column("volume", Float),
    Column("amount", Float),
    Column("pct_chg", Float),
    Column("price", Float),
    UniqueConstraint("ts_code", "dt", name="uq_daily_code_dt"),
)

# 复合索引加速查询
Index("ix_daily_code_dt", t_daily_prices.c.ts_code, t_daily_prices.c.dt)
Index("ix_daily_dt", t_daily_prices.c.dt)

t_minute_prices = Table(
    "astock_minute_prices", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("ts_code", String(20), nullable=False),
    Column("freq", String(10), nullable=False),
    Column("dt", DateTime, nullable=False),
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float),
    Column("vol", Float),
    Column("amount", Float),
    Column("price", Float),
    UniqueConstraint("ts_code", "freq", "dt", name="uq_minute_code_freq_dt"),
)

Index("ix_minute_code_freq_dt", t_minute_prices.c.ts_code, t_minute_prices.c.freq, t_minute_prices.c.dt)

t_instruments = Table(
    "astock_instruments", metadata,
    Column("instrument", String(20), primary_key=True),
    Column("description", String(100)),
    Column("pointsize", Float, default=1.0),
    Column("currency", String(10), default="CNY"),
    Column("asset_class", String(20), default="Equity"),
    Column("per_block", Float, default=0.0),
    Column("percentage", Float, default=0.00025),
    Column("per_trade", Float, default=0.001),
    Column("region", String(10), default="CN"),
)

t_spread_costs = Table(
    "astock_spread_costs", metadata,
    Column("instrument", String(20), primary_key=True),
    Column("spread_cost", Float, default=0.0005),
)

t_valid_symbols = Table(
    "astock_valid_symbols", metadata,
    Column("instrument", String(20), primary_key=True),
    Column("discovered_at", DateTime, default=datetime.now),
)


def create_all_tables(engine):
    """创建所有表 (如果不存在)"""
    metadata.create_all(engine)
    logger.info("All astock tables created/verified")


# ── 日线价格 ────────────────────────────────────────────────────

class PGDailyPricesData:
    """
    PostgreSQL 日线价格存储

    接口与 AStockDailyPricesData 完全一致。
    """

    def __init__(self, engine=None):
        if engine is None:
            from sysdata.astock.db_config import get_engine
            engine = get_engine()
        self._engine = engine
        create_all_tables(engine)

    def __repr__(self):
        return f"PGDailyPricesData @ {self._engine.url}"

    # ── read ───────────────────────────────────────────────────

    def get_list_of_instruments(self) -> List[str]:
        sql = text("SELECT DISTINCT ts_code FROM astock_daily_prices ORDER BY ts_code")
        with self._engine.connect() as conn:
            result = conn.execute(sql)
            return [row[0] for row in result]

    def get_prices(self, ts_code: str) -> pd.Series:
        """返回 pd.Series, index=DatetimeIndex, values=close price"""
        sql = text(
            "SELECT dt, price FROM astock_daily_prices "
            "WHERE ts_code = :code ORDER BY dt"
        )
        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={"code": ts_code}, parse_dates=["dt"])
        if df.empty:
            return pd.Series(dtype=float)
        s = df.set_index("dt")["price"]
        s.index.name = "DATETIME"
        s.name = "price"
        return s

    get_adjusted_prices = property(lambda self: self.get_prices)

    def get_prices_dataframe(self, ts_code: str) -> pd.DataFrame:
        """返回完整 OHLCV DataFrame"""
        sql = text(
            "SELECT dt, open, high, low, close, volume, amount, pct_chg, price "
            "FROM astock_daily_prices WHERE ts_code = :code ORDER BY dt"
        )
        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={"code": ts_code}, parse_dates=["dt"])
        if df.empty:
            return pd.DataFrame()
        df = df.set_index("dt")
        df.index.name = "DATETIME"
        return df

    # ── write ──────────────────────────────────────────────────

    def add_prices(self, ts_code: str, price_series: pd.Series):
        """写入/覆盖价格"""
        df = pd.DataFrame({"price": price_series})
        df["ts_code"] = ts_code
        df["dt"] = df.index
        self._upsert_daily(df[["ts_code", "dt", "price"]])

    def add_ohlcv(self, ts_code: str, ohlcv_df: pd.DataFrame):
        """写入完整 OHLCV"""
        df = ohlcv_df.copy()
        if "price" not in df.columns and "close" in df.columns:
            df["price"] = df["close"]
        df["ts_code"] = ts_code
        df["dt"] = df.index
        cols = ["ts_code", "dt", "open", "high", "low", "close",
                "volume", "amount", "pct_chg", "price"]
        cols = [c for c in cols if c in df.columns]
        self._upsert_daily(df[cols])

    def append_prices(self, ts_code: str, new_df: pd.DataFrame) -> int:
        """增量追加。返回新增行数。"""
        if new_df.empty:
            return 0

        latest = self.get_latest_date(ts_code)
        if latest is not None:
            mask = new_df.index > latest
            new_rows = new_df[mask]
        else:
            new_rows = new_df

        if new_rows.empty:
            return 0

        df = new_rows.copy()
        if "price" not in df.columns and "close" in df.columns:
            df["price"] = df["close"]
        df["ts_code"] = ts_code
        df["dt"] = df.index

        cols = ["ts_code", "dt", "open", "high", "low", "close",
                "volume", "amount", "pct_chg", "price"]
        cols = [c for c in cols if c in df.columns]
        self._upsert_daily(df[cols])
        logger.info("Appended %d rows for %s (PG)", len(new_rows), ts_code)
        return len(new_rows)

    def get_latest_date(self, ts_code: str) -> Optional[pd.Timestamp]:
        sql = text(
            "SELECT MAX(dt) FROM astock_daily_prices WHERE ts_code = :code"
        )
        with self._engine.connect() as conn:
            result = conn.execute(sql, {"code": ts_code}).scalar()
        if result is None:
            return None
        return pd.Timestamp(result)

    # ── internal ───────────────────────────────────────────────

    def _upsert_daily(self, df: pd.DataFrame):
        """UPSERT (INSERT ... ON CONFLICT UPDATE)"""
        if df.empty:
            return
        records = df.to_dict("records")
        stmt = pg_insert(t_daily_prices).values(records)
        update_cols = {c.name: c for c in stmt.excluded if c.name not in ("id", "ts_code", "dt")}
        stmt = stmt.on_conflict_do_update(
            constraint="uq_daily_code_dt",
            set_=update_cols,
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)


# ── 分钟线价格 ──────────────────────────────────────────────────

class PGMinutesPricesData:
    """
    PostgreSQL 分钟线价格存储

    接口与 AStockMinutesPricesData 完全一致。
    """

    def __init__(self, engine=None):
        if engine is None:
            from sysdata.astock.db_config import get_engine
            engine = get_engine()
        self._engine = engine
        create_all_tables(engine)

    def __repr__(self):
        return f"PGMinutesPricesData @ {self._engine.url}"

    def get_list_of_instruments(self, freq: str = "1min") -> List[str]:
        sql = text(
            "SELECT DISTINCT ts_code FROM astock_minute_prices "
            "WHERE freq = :freq ORDER BY ts_code"
        )
        with self._engine.connect() as conn:
            result = conn.execute(sql, {"freq": freq})
            return [row[0] for row in result]

    def get_prices(self, ts_code: str, freq: str = "1min") -> pd.Series:
        sql = text(
            "SELECT dt, price FROM astock_minute_prices "
            "WHERE ts_code = :code AND freq = :freq ORDER BY dt"
        )
        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={"code": ts_code, "freq": freq},
                             parse_dates=["dt"])
        if df.empty:
            return pd.Series(dtype=float)
        s = df.set_index("dt")["price"]
        s.index.name = "DATETIME"
        return s.sort_index()

    def get_prices_dataframe(self, ts_code: str, freq: str = "1min") -> pd.DataFrame:
        sql = text(
            "SELECT dt, open, high, low, close, vol, amount, price "
            "FROM astock_minute_prices "
            "WHERE ts_code = :code AND freq = :freq ORDER BY dt"
        )
        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn, params={"code": ts_code, "freq": freq},
                             parse_dates=["dt"])
        if df.empty:
            return pd.DataFrame()
        df = df.set_index("dt")
        df.index.name = "DATETIME"
        return df

    def add_ohlcv(self, ts_code: str, freq: str, ohlcv_df: pd.DataFrame):
        df = ohlcv_df.copy()
        if "price" not in df.columns and "close" in df.columns:
            df["price"] = df["close"]
        df["ts_code"] = ts_code
        df["freq"] = freq
        df["dt"] = df.index
        cols = ["ts_code", "freq", "dt", "open", "high", "low", "close",
                "vol", "amount", "price"]
        cols = [c for c in cols if c in df.columns]
        self._upsert_minutes(df[cols])

    def append_prices(self, ts_code: str, freq: str, new_df: pd.DataFrame) -> int:
        if new_df.empty:
            return 0

        latest = self.get_latest_date(ts_code, freq)
        if latest is not None:
            new_rows = new_df[new_df.index > latest]
        else:
            new_rows = new_df

        if new_rows.empty:
            return 0

        df = new_rows.copy()
        if "price" not in df.columns and "close" in df.columns:
            df["price"] = df["close"]
        df["ts_code"] = ts_code
        df["freq"] = freq
        df["dt"] = df.index

        cols = ["ts_code", "freq", "dt", "open", "high", "low", "close",
                "vol", "amount", "price"]
        cols = [c for c in cols if c in df.columns]
        self._upsert_minutes(df[cols])
        logger.info("Appended %d rows (%s) for %s (PG)", len(new_rows), freq, ts_code)
        return len(new_rows)

    def get_latest_date(self, ts_code: str, freq: str = "1min") -> Optional[pd.Timestamp]:
        sql = text(
            "SELECT MAX(dt) FROM astock_minute_prices "
            "WHERE ts_code = :code AND freq = :freq"
        )
        with self._engine.connect() as conn:
            result = conn.execute(sql, {"code": ts_code, "freq": freq}).scalar()
        if result is None:
            return None
        return pd.Timestamp(result)

    def _upsert_minutes(self, df: pd.DataFrame):
        if df.empty:
            return
        records = df.to_dict("records")
        stmt = pg_insert(t_minute_prices).values(records)
        update_cols = {c.name: c for c in stmt.excluded
                       if c.name not in ("id", "ts_code", "freq", "dt")}
        stmt = stmt.on_conflict_do_update(
            constraint="uq_minute_code_freq_dt",
            set_=update_cols,
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)


# ── Instrument 元信息 ───────────────────────────────────────────

class PGInstrumentData:
    """
    PostgreSQL 版品种元信息

    接口与 AStockInstrumentData 完全一致。
    """

    def __init__(self, engine=None):
        if engine is None:
            from sysdata.astock.db_config import get_engine
            engine = get_engine()
        self._engine = engine
        create_all_tables(engine)
        self._cache = None

    def __repr__(self):
        return f"PGInstrumentData @ {self._engine.url}"

    def get_list_of_instruments(self) -> List[str]:
        return list(self.get_all_instrument_data_as_df().index)

    def get_all_instrument_data_as_df(self) -> pd.DataFrame:
        if self._cache is not None:
            return self._cache
        sql = text("SELECT * FROM astock_instruments ORDER BY instrument")
        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn)
        if df.empty:
            return pd.DataFrame()
        df.index = df["instrument"]
        df.drop(columns=["instrument"], inplace=True)
        # 重命名列以兼容 CSV 版本
        rename_map = {
            "description": "Description",
            "pointsize": "Pointsize",
            "currency": "Currency",
            "asset_class": "AssetClass",
            "per_block": "PerBlock",
            "percentage": "Percentage",
            "per_trade": "PerTrade",
            "region": "Region",
        }
        df.rename(columns=rename_map, inplace=True)
        self._cache = df
        return df

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

    def invalidate_cache(self):
        self._cache = None

    # ── write ──────────────────────────────────────────────────

    def upsert_instrument(self, instrument_code: str, meta: dict):
        """插入或更新品种元信息"""
        record = {
            "instrument": instrument_code,
            "description": meta.get("Description", instrument_code),
            "pointsize": meta.get("Pointsize", 1.0),
            "currency": meta.get("Currency", "CNY"),
            "asset_class": meta.get("AssetClass", "Equity"),
            "per_block": meta.get("PerBlock", 0.0),
            "percentage": meta.get("Percentage", 0.00025),
            "per_trade": meta.get("PerTrade", 0.001),
            "region": meta.get("Region", "CN"),
        }
        stmt = pg_insert(t_instruments).values([record])
        update_cols = {c.name: c for c in stmt.excluded if c.name != "instrument"}
        stmt = stmt.on_conflict_do_update(
            index_elements=["instrument"],
            set_=update_cols,
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)
        self._cache = None

    def bulk_upsert(self, instruments_df: pd.DataFrame):
        """批量插入品种元信息 (从 CSV sync 迁移)"""
        if instruments_df.empty:
            return
        records = []
        for idx, row in instruments_df.iterrows():
            records.append({
                "instrument": idx if isinstance(idx, str) else row.get("Instrument", idx),
                "description": row.get("Description", str(idx)),
                "pointsize": row.get("Pointsize", 1.0),
                "currency": row.get("Currency", "CNY"),
                "asset_class": row.get("AssetClass", "Equity"),
                "per_block": row.get("PerBlock", 0.0),
                "percentage": row.get("Percentage", 0.00025),
                "per_trade": row.get("PerTrade", 0.001),
                "region": row.get("Region", "CN"),
            })
        stmt = pg_insert(t_instruments).values(records)
        update_cols = {c.name: c for c in stmt.excluded if c.name != "instrument"}
        stmt = stmt.on_conflict_do_update(
            index_elements=["instrument"],
            set_=update_cols,
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)
        self._cache = None
        logger.info("Bulk upserted %d instruments (PG)", len(records))

    @staticmethod
    def _default_meta(instrument_code: str) -> dict:
        return {
            "Description": instrument_code,
            "Pointsize": 1.0,
            "Currency": "CNY",
            "AssetClass": "Equity",
            "PerBlock": 0.0,
            "Percentage": 0.00025,
            "PerTrade": 0.001,
            "Region": "CN",
        }


# ── SpreadCost ──────────────────────────────────────────────────

class PGSpreadCostData:
    """
    PostgreSQL 版滑点成本

    接口与 AStockSpreadCostData 完全一致。
    """

    def __init__(self, engine=None):
        if engine is None:
            from sysdata.astock.db_config import get_engine
            engine = get_engine()
        self._engine = engine
        create_all_tables(engine)
        self._cache = None

    def __repr__(self):
        return f"PGSpreadCostData @ {self._engine.url}"

    def get_spread_cost(self, instrument_code: str) -> float:
        series = self.get_spread_costs_as_series()
        if instrument_code in series.index:
            return float(series[instrument_code])
        return 0.0005

    def get_spread_costs_as_series(self) -> pd.Series:
        if self._cache is not None:
            return self._cache
        sql = text("SELECT instrument, spread_cost FROM astock_spread_costs ORDER BY instrument")
        with self._engine.connect() as conn:
            df = pd.read_sql(sql, conn)
        if df.empty:
            return pd.Series(dtype=float)
        df.index = df["instrument"]
        series = df["spread_cost"]
        series.index.name = "Instrument"
        self._cache = series
        return series

    def get_list_of_instruments(self) -> List[str]:
        return list(self.get_spread_costs_as_series().index)

    def invalidate_cache(self):
        self._cache = None

    # ── write ──────────────────────────────────────────────────

    def upsert_spread_cost(self, instrument_code: str, cost: float):
        record = {"instrument": instrument_code, "spread_cost": cost}
        stmt = pg_insert(t_spread_costs).values([record])
        stmt = stmt.on_conflict_do_update(
            index_elements=["instrument"],
            set_={"spread_cost": stmt.excluded.spread_cost},
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)
        self._cache = None

    def bulk_upsert(self, spread_dict: dict):
        """批量插入 {instrument: spread_cost}"""
        if not spread_dict:
            return
        records = [{"instrument": k, "spread_cost": v} for k, v in spread_dict.items()]
        stmt = pg_insert(t_spread_costs).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["instrument"],
            set_={"spread_cost": stmt.excluded.spread_cost},
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)
        self._cache = None
        logger.info("Bulk upserted %d spread costs (PG)", len(records))


# ── Valid Symbols ───────────────────────────────────────────────

class PGValidSymbols:
    """PG 版有效品种管理"""

    def __init__(self, engine=None):
        if engine is None:
            from sysdata.astock.db_config import get_engine
            engine = get_engine()
        self._engine = engine
        create_all_tables(engine)

    def load_valid_symbols(self) -> List[str]:
        sql = text("SELECT instrument FROM astock_valid_symbols ORDER BY instrument")
        with self._engine.connect() as conn:
            result = conn.execute(sql)
            return [row[0] for row in result]

    def save_valid_symbols(self, symbols: List[str]):
        """覆盖写入"""
        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM astock_valid_symbols"))
            if symbols:
                records = [{"instrument": s, "discovered_at": datetime.now()} for s in sorted(set(symbols))]
                conn.execute(t_valid_symbols.insert(), records)
        logger.info("Saved %d valid symbols (PG)", len(symbols))

    def update_valid_symbols(self, new_symbols: List[str]):
        """增量更新"""
        existing = set(self.load_valid_symbols())
        existing.update(new_symbols)
        self.save_valid_symbols(sorted(existing))
