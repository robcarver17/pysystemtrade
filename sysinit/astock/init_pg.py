"""
A-Stock PostgreSQL 初始化 & Parquet → PG 数据迁移

用法:
    # 创建数据库 + 表
    python -m sysinit.astock.init_pg --create-db

    # 仅建表 (数据库已存在)
    python -m sysinit.astock.init_pg --create-tables

    # 从 Parquet 迁移数据到 PG
    python -m sysinit.astock.init_pg --migrate

    # 一步到位: 建库 + 建表 + 迁移
    python -m sysinit.astock.init_pg --all

    # 验证 PG 数据
    python -m sysinit.astock.init_pg --verify

    # 显示 PG 表统计
    python -m sysinit.astock.init_pg --stats
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("astock.init_pg")

REPO_ROOT = Path(__file__).resolve().parents[2]


def create_database():
    """创建 astock 数据库 (如果不存在)"""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    from sysdata.astock.db_config import get_pg_url

    url = get_pg_url()
    # 解析出 dbname
    if "/" in url.split("@")[-1]:
        dbname = url.rsplit("/", 1)[-1].split("?")[0]
    else:
        dbname = "astock"

    # 连接到默认 postgres 数据库
    base_url = url.rsplit("/", 1)[0] + "/postgres"
    # 从 sqlalchemy URL 提取连接参数
    from sqlalchemy import make_url
    parsed = make_url(base_url)

    conn = psycopg2.connect(
        host=parsed.host or "localhost",
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password or "",
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
    if cur.fetchone():
        logger.info("Database '%s' already exists", dbname)
    else:
        cur.execute(f'CREATE DATABASE "{dbname}"')
        logger.info("Database '%s' created", dbname)

    cur.close()
    conn.close()


def create_tables():
    """创建所有表"""
    from sysdata.astock.db_config import get_engine
    from sysdata.astock.astock_pg import create_all_tables
    engine = get_engine()
    create_all_tables(engine)
    logger.info("All tables created/verified")


def migrate_parquet_to_pg():
    """从 Parquet 文件迁移数据到 PostgreSQL"""
    from sysdata.astock.astock_prices import AStockDailyPricesData, AStockMinutesPricesData
    from sysdata.astock.astock_instruments import AStockInstrumentData, AStockSpreadCostData
    from sysdata.astock.astock_pg import (
        PGDailyPricesData, PGMinutesPricesData,
        PGInstrumentData, PGSpreadCostData, PGValidSymbols,
    )
    from sysdata.astock.universe import AStockUniverse
    from sysdata.astock.db_config import get_engine

    engine = get_engine()

    # ── 1. Instrument Config ──────────────────────────────────
    logger.info("=== Migrating Instrument Config ===")
    try:
        csv_instr = AStockInstrumentData()
        df = csv_instr.get_all_instrument_data_as_df()
        if not df.empty:
            pg_instr = PGInstrumentData(engine)
            pg_instr.bulk_upsert(df)
            logger.info("Migrated %d instruments", len(df))
        else:
            logger.info("No instrument config to migrate")
    except Exception as e:
        logger.warning("Instrument config migration skipped: %s", e)

    # ── 2. Spread Costs ───────────────────────────────────────
    logger.info("=== Migrating Spread Costs ===")
    try:
        csv_spread = AStockSpreadCostData()
        series = csv_spread.get_spread_costs_as_series()
        if not series.empty:
            pg_spread = PGSpreadCostData(engine)
            pg_spread.bulk_upsert(series.to_dict())
            logger.info("Migrated %d spread costs", len(series))
        else:
            logger.info("No spread costs to migrate")
    except Exception as e:
        logger.warning("Spread costs migration skipped: %s", e)

    # ── 3. Daily Prices ───────────────────────────────────────
    logger.info("=== Migrating Daily Prices ===")
    pq_daily = AStockDailyPricesData()
    pg_daily = PGDailyPricesData(engine)

    instruments = pq_daily.get_list_of_instruments()
    logger.info("Found %d instruments in Parquet daily store", len(instruments))

    for i, code in enumerate(instruments):
        try:
            df = pq_daily.get_prices_dataframe(code)
            if df.empty:
                continue
            # 直接写入 PG (使用 upsert)
            df_copy = df.copy()
            if "price" not in df_copy.columns and "close" in df_copy.columns:
                df_copy["price"] = df_copy["close"]
            df_copy["ts_code"] = code
            df_copy["dt"] = df_copy.index

            cols = ["ts_code", "dt", "open", "high", "low", "close",
                    "volume", "amount", "pct_chg", "price"]
            cols = [c for c in cols if c in df_copy.columns]
            pg_daily._upsert_daily(df_copy[cols])

            if (i + 1) % 10 == 0:
                logger.info("Daily progress: %d/%d", i + 1, len(instruments))
        except Exception as e:
            logger.error("Error migrating daily %s: %s", code, e)

    logger.info("Daily migration complete")

    # ── 4. Minutes Prices ─────────────────────────────────────
    logger.info("=== Migrating Minutes Prices ===")
    pq_mins = AStockMinutesPricesData()
    pg_mins = PGMinutesPricesData(engine)

    for freq in ["1min", "5min", "15min", "30min", "60min"]:
        instruments = pq_mins.get_list_of_instruments(freq)
        if not instruments:
            continue
        logger.info("Migrating %d instruments for %s", len(instruments), freq)

        for i, code in enumerate(instruments):
            try:
                df = pq_mins.get_prices_dataframe(code, freq)
                if df.empty:
                    continue
                df_copy = df.copy()
                if "price" not in df_copy.columns and "close" in df_copy.columns:
                    df_copy["price"] = df_copy["close"]
                df_copy["ts_code"] = code
                df_copy["freq"] = freq
                df_copy["dt"] = df_copy.index

                cols = ["ts_code", "freq", "dt", "open", "high", "low",
                        "close", "vol", "amount", "price"]
                cols = [c for c in cols if c in df_copy.columns]
                pg_mins._upsert_minutes(df_copy[cols])
            except Exception as e:
                logger.error("Error migrating %s %s: %s", freq, code, e)

    logger.info("Minutes migration complete")

    # ── 5. Valid Symbols ──────────────────────────────────────
    logger.info("=== Migrating Valid Symbols ===")
    valid = AStockUniverse.load_valid_symbols()
    if valid:
        pg_valid = PGValidSymbols(engine)
        pg_valid.save_valid_symbols(valid)
        logger.info("Migrated %d valid symbols", len(valid))

    logger.info("=== Migration Complete ===")


def verify_pg_data():
    """验证 PG 数据完整性"""
    from sysdata.astock.astock_prices import AStockDailyPricesData
    from sysdata.astock.astock_pg import PGDailyPricesData
    from sysdata.astock.db_config import get_engine

    engine = get_engine()
    pq = AStockDailyPricesData()
    pg = PGDailyPricesData(engine)

    pq_instruments = pq.get_list_of_instruments()
    pg_instruments = pg.get_list_of_instruments()

    print(f"\n{'='*50}")
    print(f"Verification: Parquet vs PostgreSQL")
    print(f"{'='*50}")
    print(f"Parquet instruments: {len(pq_instruments)}")
    print(f"PG instruments:      {len(pg_instruments)}")

    # 比较每个品种的行数
    mismatches = []
    for code in pq_instruments:
        pq_prices = pq.get_prices(code)
        pg_prices = pg.get_prices(code)
        if len(pq_prices) != len(pg_prices):
            mismatches.append((code, len(pq_prices), len(pg_prices)))
        else:
            print(f"  ✓ {code}: {len(pq_prices)} rows match")

    if mismatches:
        print(f"\nMismatches:")
        for code, pq_n, pg_n in mismatches:
            print(f"  ✗ {code}: parquet={pq_n}, pg={pg_n}")
    else:
        print(f"\nAll data matches! ✓")
    print(f"{'='*50}")


def show_pg_stats():
    """显示 PG 表统计"""
    from sysdata.astock.db_config import get_engine
    from sqlalchemy import text

    engine = get_engine()

    stats_queries = {
        "astock_daily_prices": "SELECT COUNT(*) as rows, COUNT(DISTINCT ts_code) as instruments, MIN(dt) as earliest, MAX(dt) as latest FROM astock_daily_prices",
        "astock_minute_prices": "SELECT COUNT(*) as rows, COUNT(DISTINCT ts_code) as instruments, COUNT(DISTINCT freq) as freqs FROM astock_minute_prices",
        "astock_instruments": "SELECT COUNT(*) as rows FROM astock_instruments",
        "astock_spread_costs": "SELECT COUNT(*) as rows FROM astock_spread_costs",
        "astock_valid_symbols": "SELECT COUNT(*) as rows FROM astock_valid_symbols",
    }

    print(f"\n{'='*60}")
    print(f"PostgreSQL A-Stock Data Statistics")
    print(f"{'='*60}")

    with engine.connect() as conn:
        for table, sql in stats_queries.items():
            try:
                result = conn.execute(text(sql))
                row = result.fetchone()
                print(f"\n{table}:")
                for i, col in enumerate(result.keys()):
                    print(f"  {col}: {row[i]}")
            except Exception as e:
                print(f"\n{table}: (not found or error: {e})")

    # DB size
    with engine.connect() as conn:
        try:
            result = conn.execute(text(
                "SELECT pg_size_pretty(pg_database_size(current_database())) as db_size"
            ))
            row = result.fetchone()
            print(f"\nDatabase size: {row[0]}")
        except Exception:
            pass

    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="A-Stock PostgreSQL 初始化 & 迁移",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--create-db", action="store_true", help="创建数据库")
    parser.add_argument("--create-tables", action="store_true", help="创建表")
    parser.add_argument("--migrate", action="store_true", help="从 Parquet 迁移到 PG")
    parser.add_argument("--verify", action="store_true", help="验证 PG 数据")
    parser.add_argument("--stats", action="store_true", help="显示 PG 统计")
    parser.add_argument("--all", action="store_true", help="建库 + 建表 + 迁移")

    args = parser.parse_args()

    if not any([args.create_db, args.create_tables, args.migrate,
                args.verify, args.stats, args.all]):
        parser.print_help()
        return

    if args.all or args.create_db:
        create_database()

    if args.all or args.create_tables:
        create_tables()

    if args.all or args.migrate:
        migrate_parquet_to_pg()

    if args.verify:
        verify_pg_data()

    if args.all or args.stats:
        show_pg_stats()


if __name__ == "__main__":
    main()
