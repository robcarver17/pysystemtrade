"""
A-Stock 数据后端配置 — PG / Parquet 开关

通过环境变量 ASTOCK_BACKEND 控制数据存储后端:
    - "parquet"  (默认) — 使用本地 Parquet 文件
    - "pg" / "postgresql" — 使用 PostgreSQL

PG 连接通过 ASTOCK_PG_URL 环境变量配置:
    postgresql://user:password@host:port/dbname

用法:
    from sysdata.astock.db_config import get_backend, get_engine, BackendType

    if get_backend() == BackendType.PG:
        engine = get_engine()
        ...
"""

import os
import logging
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Load .env
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(_ENV_FILE)
except ImportError:
    pass


class BackendType(Enum):
    PARQUET = "parquet"
    PG = "pg"


# ── 全局配置 ────────────────────────────────────────────────────

DEFAULT_PG_URL = "postgresql://wenxuanliu@localhost:5432/astock"

def get_backend() -> BackendType:
    """获取当前后端类型"""
    val = os.environ.get("ASTOCK_BACKEND", "parquet").lower().strip()
    if val in ("pg", "postgresql", "postgres"):
        return BackendType.PG
    return BackendType.PARQUET


def get_pg_url() -> str:
    """获取 PostgreSQL 连接 URL"""
    return os.environ.get("ASTOCK_PG_URL", DEFAULT_PG_URL)


def is_pg_enabled() -> bool:
    """快捷检查: PG 后端是否启用"""
    return get_backend() == BackendType.PG


# ── SQLAlchemy Engine 单例 ──────────────────────────────────────

_engine = None

def get_engine():
    """
    获取 SQLAlchemy Engine (全局单例, 自带连接池)

    Returns:
        sqlalchemy.Engine
    """
    global _engine
    if _engine is not None:
        return _engine

    from sqlalchemy import create_engine

    url = get_pg_url()
    _engine = create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )
    logger.info("PostgreSQL engine created: %s", _mask_url(url))
    return _engine


def dispose_engine():
    """关闭引擎及其连接池"""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
        logger.info("PostgreSQL engine disposed")


def _mask_url(url: str) -> str:
    """隐藏密码的URL显示"""
    if "@" in url and ":" in url.split("@")[0]:
        prefix, rest = url.split("@", 1)
        parts = prefix.rsplit(":", 1)
        if len(parts) == 2 and "//" in parts[0]:
            return f"{parts[0]}:***@{rest}"
    return url


# ── 工厂函数: 获取正确的 Store 实例 ────────────────────────────

def get_daily_prices_store():
    """根据后端配置返回日线价格 Store"""
    if is_pg_enabled():
        from sysdata.astock.astock_pg import PGDailyPricesData
        return PGDailyPricesData(engine=get_engine())
    else:
        from sysdata.astock.astock_prices import AStockDailyPricesData
        return AStockDailyPricesData()


def get_minutes_prices_store():
    """根据后端配置返回分钟线价格 Store"""
    if is_pg_enabled():
        from sysdata.astock.astock_pg import PGMinutesPricesData
        return PGMinutesPricesData(engine=get_engine())
    else:
        from sysdata.astock.astock_prices import AStockMinutesPricesData
        return AStockMinutesPricesData()


def get_instrument_data_store():
    """根据后端配置返回 Instrument 元数据 Store"""
    if is_pg_enabled():
        from sysdata.astock.astock_pg import PGInstrumentData
        return PGInstrumentData(engine=get_engine())
    else:
        from sysdata.astock.astock_instruments import AStockInstrumentData
        return AStockInstrumentData()


def get_spread_cost_store():
    """根据后端配置返回 SpreadCost Store"""
    if is_pg_enabled():
        from sysdata.astock.astock_pg import PGSpreadCostData
        return PGSpreadCostData(engine=get_engine())
    else:
        from sysdata.astock.astock_instruments import AStockSpreadCostData
        return AStockSpreadCostData()
