#!/usr/bin/env python3
"""
sync_to_remote_pg.py - 同步本地 A股 PostgreSQL 数据到远程 Supabase

用法:
    cd /Users/wenxuanliu/TradeAll/pysystemtrade
    python sysinit/astock/sync_to_remote_pg.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text

# Remote Supabase connection
REMOTE_HOST = 'db.grvepurdpupmjebbcjhp.supabase.co'
REMOTE_PORT = 5432
REMOTE_DB = 'postgres'
REMOTE_USER = 'postgres'
REMOTE_PASS = 'Tridentpoint1010!'

LOCAL_URL = 'postgresql://wenxuanliu@localhost:5432/astock'


def get_remote_conn():
    """获取远程数据库连接 (使用 SQLAlchemy + SSL)"""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool
    
    # Connection string with SSL options
    conn_str = (
        f"postgresql://{REMOTE_USER}:{REMOTE_PASS}@{REMOTE_HOST}:{REMOTE_PORT}/{REMOTE_DB}"
        f"?sslmode=require&connect_timeout=30"
    )
    
    engine = create_engine(conn_str, poolclass=NullPool)
    return engine.raw_connection()


def create_remote_tables(conn):
    """在远程数据库创建 A股表结构"""
    cur = conn.cursor()
    
    tables = [
        # Daily prices
        """
        CREATE TABLE IF NOT EXISTS astock_daily_prices (
            id BIGSERIAL PRIMARY KEY,
            ts_code VARCHAR(20) NOT NULL,
            dt TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            open DOUBLE PRECISION,
            high DOUBLE PRECISION,
            low DOUBLE PRECISION,
            close DOUBLE PRECISION,
            volume DOUBLE PRECISION,
            amount DOUBLE PRECISION,
            pct_chg DOUBLE PRECISION,
            price DOUBLE PRECISION,
            CONSTRAINT uq_daily_code_dt UNIQUE (ts_code, dt)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_daily_code_dt ON astock_daily_prices (ts_code, dt)",
        "CREATE INDEX IF NOT EXISTS ix_daily_dt ON astock_daily_prices (dt)",
        
        # Instruments
        """
        CREATE TABLE IF NOT EXISTS astock_instruments (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL UNIQUE,
            name VARCHAR(100),
            exchange VARCHAR(20),
            currency VARCHAR(10) DEFAULT 'CNY',
            instrument_type VARCHAR(20),
            sector VARCHAR(50),
            industry VARCHAR(50),
            list_date DATE,
            delisted BOOLEAN DEFAULT FALSE,
            pointsize DOUBLE PRECISION DEFAULT 1.0,
            big_pointvalue DOUBLE PRECISION DEFAULT 1.0,
            meta JSONB
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_instruments_symbol ON astock_instruments (symbol)",
        
        # Spread costs
        """
        CREATE TABLE IF NOT EXISTS astock_spread_costs (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL UNIQUE,
            spread_cost DOUBLE PRECISION DEFAULT 0.0,
            last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_spread_symbol ON astock_spread_costs (symbol)",
        
        # Valid symbols
        """
        CREATE TABLE IF NOT EXISTS astock_valid_symbols (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL UNIQUE,
            first_date DATE,
            last_date DATE,
            row_count INTEGER,
            last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_valid_symbol ON astock_valid_symbols (symbol)",
    ]
    
    print("Creating remote tables...")
    for sql in tables:
        cur.execute(sql)
    conn.commit()
    print("  Tables created/verified")
    cur.close()


def sync_daily_prices(local_engine, remote_conn):
    """同步日线数据 (大批量)"""
    print("\nSyncing astock_daily_prices...")
    
    df = pd.read_sql("SELECT ts_code, dt, open, high, low, close, volume, amount, pct_chg, price FROM astock_daily_prices ORDER BY ts_code, dt", local_engine)
    print(f"  Local rows: {len(df):,}")
    
    if df.empty:
        print("  No data to sync")
        return
    
    cur = remote_conn.cursor()
    
    # Truncate and insert
    cur.execute("TRUNCATE TABLE astock_daily_prices CASCADE")
    
    # Batch insert
    rows = [tuple(row) for row in df.values]
    chunk_size = 5000
    total = len(rows)
    
    for i in range(0, total, chunk_size):
        chunk = rows[i:i+chunk_size]
        execute_values(
            cur,
            """
            INSERT INTO astock_daily_prices (ts_code, dt, open, high, low, close, volume, amount, pct_chg, price)
            VALUES %s
            ON CONFLICT (ts_code, dt) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                amount = EXCLUDED.amount,
                pct_chg = EXCLUDED.pct_chg,
                price = EXCLUDED.price
            """,
            chunk
        )
        remote_conn.commit()
        print(f"  Uploaded {min(i+chunk_size, total):,}/{total:,}", end='\r')
    
    cur.close()
    print(f"\n  Synced {total:,} rows")


def sync_simple_table(local_engine, remote_conn, table_name, columns):
    """同步小表 (instruments, spread_costs, valid_symbols)"""
    print(f"\nSyncing {table_name}...")
    
    df = pd.read_sql(f"SELECT {columns} FROM {table_name}", local_engine)
    print(f"  Local rows: {len(df):,}")
    
    if df.empty:
        print("  No data to sync")
        return
    
    cur = remote_conn.cursor()
    cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")
    
    rows = [tuple(row) for row in df.values]
    cols = [c.strip() for c in columns.split(',')]
    
    # Build INSERT SQL
    col_str = ', '.join(cols)
    placeholders = ', '.join(['%s'] * len(cols))
    
    for row in rows:
        cur.execute(f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})", row)
    
    remote_conn.commit()
    cur.close()
    print(f"  Synced {len(rows):,} rows")


def verify_sync(local_engine, remote_conn):
    """验证同步结果"""
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)
    
    tables = [
        ('astock_daily_prices', 'volume'),
        ('astock_instruments', 'exchange'),
        ('astock_spread_costs', 'spread_cost'),
        ('astock_valid_symbols', 'row_count'),
    ]
    
    cur = remote_conn.cursor()
    
    for table, _ in tables:
        local_cnt = pd.read_sql(f"SELECT COUNT(*) as cnt FROM {table}", local_engine).iloc[0]['cnt']
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        remote_cnt = cur.fetchone()[0]
        status = "✓" if local_cnt == remote_cnt else "✗"
        print(f"{status} {table}: local={local_cnt:,}, remote={remote_cnt:,}")
    
    cur.close()


def main():
    print("=" * 60)
    print("A-Stock PostgreSQL Remote Sync → Supabase")
    print("=" * 60)
    print(f"Local:  {LOCAL_URL}")
    print(f"Remote: {REMOTE_HOST}:{REMOTE_PORT}/{REMOTE_DB}")
    
    # Connect
    print("\nConnecting...")
    local_engine = create_engine(LOCAL_URL)
    remote_conn = get_remote_conn()
    
    # Test
    with local_engine.connect() as conn:
        local_ver = conn.execute(text("SELECT version()")).scalar()
    cur = remote_conn.cursor()
    cur.execute("SELECT version()")
    remote_ver = cur.fetchone()[0]
    cur.close()
    
    print(f"  Local:  {local_ver[:40]}")
    print(f"  Remote: {remote_ver[:40]}")
    
    # Create tables
    create_remote_tables(remote_conn)
    
    # Sync data
    sync_daily_prices(local_engine, remote_conn)
    sync_simple_table(local_engine, remote_conn, 'astock_instruments', 
                     'instrument, description, pointsize, currency, asset_class, per_block, percentage, per_trade, region')
    sync_simple_table(local_engine, remote_conn, 'astock_spread_costs', 'symbol, spread_cost')
    sync_simple_table(local_engine, remote_conn, 'astock_valid_symbols', 'symbol, first_date, last_date, row_count')
    
    # Verify
    verify_sync(local_engine, remote_conn)
    
    remote_conn.close()
    
    print("\n" + "=" * 60)
    print("Sync complete!")
    print("=" * 60)
    print(f"\nRemote DB URL for .env:")
    print(f'  ASTOCK_PG_URL="postgresql://{REMOTE_USER}:{REMOTE_PASS}@{REMOTE_HOST}:{REMOTE_PORT}/{REMOTE_DB}"')


if __name__ == '__main__':
    main()
