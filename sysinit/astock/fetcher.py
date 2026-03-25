"""
A-stock data fetcher — 全市场定时调度增量拉取

从 xiximiao API 拉取 A股日线/分钟线数据，存入 Parquet。
支持增量更新、全市场扫描、交易日历调度、自动发现有效品种、
动态生成 instrumentconfig/spreadcosts。

用法:
    # 一次性拉取 (测试)
    python -m sysinit.astock.fetcher --once --freq daily --universe test

    # 一次性拉取全市场（首次）
    python -m sysinit.astock.fetcher --once --freq daily --universe all --years 5

    # 持续运行 (pm2 管理)
    python -m sysinit.astock.fetcher --freq daily --universe valid

    # 全市场扫描 — 发现有效品种
    python -m sysinit.astock.fetcher --scan --universe full

    # 查看市场状态
    python -m sysinit.astock.fetcher --status

    # 查看数据统计
    python -m sysinit.astock.fetcher --info

    # 强制拉取 (忽略交易时间)
    python -m sysinit.astock.fetcher --once --force --freq daily --universe popular

    # 指定品种
    python -m sysinit.astock.fetcher --once --freq daily --symbols 600519.SH 000858.SZ

    # 同步 instrumentconfig (根据已有数据自动生成)
    python -m sysinit.astock.fetcher --sync-config
"""

import argparse
import logging
import time
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd

from sysdata.astock.xiximiao_client import XiximiaoClient
from sysdata.astock.db_config import (
    get_daily_prices_store, get_minutes_prices_store,
    get_instrument_data_store, get_spread_cost_store,
    is_pg_enabled, get_backend, BackendType,
)
from sysdata.astock.universe import AStockUniverse
from sysdata.astock.china_calendar import ChinaMarketCalendar

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("astock.fetcher")

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "data" / "astock" / "csvconfig"


# ── 数据标准化 ──────────────────────────────────────────────────

def _normalize_daily(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tushare daily → 标准 OHLCV DataFrame (DatetimeIndex)

    输入列: ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
    输出列: open, high, low, close, volume, amount, pct_chg, price  (index=DatetimeIndex)
    """
    if df.empty:
        return df
    df = df.copy()
    df["DATETIME"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    df = df.set_index("DATETIME").sort_index()
    df["volume"] = df["vol"] * 100  # 手 → 股
    df["price"] = df["close"]
    cols = ["open", "high", "low", "close", "volume", "amount", "pct_chg", "price"]
    return df[[c for c in cols if c in df.columns]]


def _normalize_minutes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tushare stk_mins → 标准 OHLCV DataFrame (DatetimeIndex)

    输入列: ts_code, trade_time, close, open, high, low, vol, amount
    输出列: open, high, low, close, vol, amount, price  (index=DatetimeIndex)
    """
    if df.empty:
        return df
    df = df.copy()
    df["DATETIME"] = pd.to_datetime(df["trade_time"])
    df = df.set_index("DATETIME").sort_index()
    df["price"] = df["close"]
    cols = ["open", "high", "low", "close", "vol", "amount", "price"]
    return df[[c for c in cols if c in df.columns]]


def _estimate_spread_cost(avg_price: float) -> float:
    """根据平均价格估算 SpreadCost (half-tick / price)"""
    if avg_price <= 0:
        return 0.001
    tick = 0.01  # A股最小变动价位
    cost = (tick / 2) / avg_price
    return round(max(cost, 0.0001), 6)


# ── Config 自动同步 ──────────────────────────────────────────────

def sync_instrument_config(daily_store):
    """
    根据已存储的日线数据自动生成/更新 instrument config 和 spread costs。

    PG 后端: 直接写入 astock_instruments / astock_spread_costs 表
    Parquet 后端: 写入 CSV 文件
    """
    instruments = daily_store.get_list_of_instruments()
    if not instruments:
        logger.warning("No instruments in daily store, skipping config sync")
        return

    use_pg = is_pg_enabled()

    if use_pg:
        _sync_config_pg(daily_store, instruments)
    else:
        _sync_config_csv(daily_store, instruments)


def _sync_config_pg(daily_store, instruments):
    """PG 后端: upsert instrument config + spread costs"""
    from sysdata.astock.astock_pg import PGInstrumentData, PGSpreadCostData
    from sysdata.astock.db_config import get_engine

    engine = get_engine()
    pg_instr = PGInstrumentData(engine)
    pg_spread = PGSpreadCostData(engine)

    existing_instruments = set(pg_instr.get_list_of_instruments())
    existing_spreads = set(pg_spread.get_list_of_instruments())

    new_config_count = 0
    new_spread_count = 0

    for code in instruments:
        if code not in existing_instruments:
            if code.startswith("51") or code.startswith("15") or code.startswith("16"):
                asset_class = "ETF"
                per_trade = 0.0
            else:
                asset_class = "Equity"
                per_trade = 0.001

            pg_instr.upsert_instrument(code, {
                "Description": code,
                "Pointsize": 1.0,
                "Currency": "CNY",
                "AssetClass": asset_class,
                "PerBlock": 0.0,
                "Percentage": 0.00025,
                "PerTrade": per_trade,
                "Region": "CN",
            })
            new_config_count += 1

        if code not in existing_spreads:
            prices = daily_store.get_prices(code)
            if not prices.empty:
                avg_price = prices.tail(20).mean()
                cost = _estimate_spread_cost(avg_price)
            else:
                cost = 0.0005
            pg_spread.upsert_spread_cost(code, cost)
            new_spread_count += 1

    logger.info(
        "Config sync (PG): %d instruments (%d new), %d spread costs (%d new)",
        len(instruments), new_config_count,
        len(instruments), new_spread_count,
    )


def _sync_config_csv(daily_store, instruments):
    """Parquet 后端: 写入 CSV 文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_file = CONFIG_DIR / "instrumentconfig.csv"
    spread_file = CONFIG_DIR / "spreadcosts.csv"

    # 加载已有 config
    existing_config = {}
    if config_file.exists():
        try:
            df = pd.read_csv(config_file)
            for _, row in df.iterrows():
                existing_config[row["Instrument"]] = row.to_dict()
        except Exception:
            pass

    existing_spread = {}
    if spread_file.exists():
        try:
            df = pd.read_csv(spread_file)
            for _, row in df.iterrows():
                existing_spread[row["Instrument"]] = row["SpreadCost"]
        except Exception:
            pass

    new_config_count = 0
    new_spread_count = 0

    for code in instruments:
        if code not in existing_config:
            if code.startswith("51") or code.startswith("15") or code.startswith("16"):
                asset_class = "ETF"
                per_trade = 0.0
            else:
                asset_class = "Equity"
                per_trade = 0.001

            existing_config[code] = {
                "Instrument": code,
                "Description": code,
                "Pointsize": 1,
                "Currency": "CNY",
                "AssetClass": asset_class,
                "PerBlock": 0,
                "Percentage": 0.00025,
                "PerTrade": per_trade,
                "Region": "CN",
            }
            new_config_count += 1

        if code not in existing_spread:
            prices = daily_store.get_prices(code)
            if not prices.empty:
                avg_price = prices.tail(20).mean()
                existing_spread[code] = _estimate_spread_cost(avg_price)
            else:
                existing_spread[code] = 0.0005
            new_spread_count += 1

    config_rows = sorted(existing_config.values(), key=lambda r: r["Instrument"])
    pd.DataFrame(config_rows).to_csv(config_file, index=False)

    spread_rows = [{"Instrument": k, "SpreadCost": v}
                   for k, v in sorted(existing_spread.items())]
    pd.DataFrame(spread_rows).to_csv(spread_file, index=False)

    logger.info(
        "Config sync (CSV): %d instruments total (%d new), %d spread costs (%d new)",
        len(config_rows), new_config_count,
        len(spread_rows), new_spread_count,
    )


# ── Fetcher ─────────────────────────────────────────────────────

class AStockFetcher:
    """
    A股数据拉取器

    功能:
      - 增量拉取日线/分钟线
      - 全市场扫描发现有效品种
      - 交易日历感知调度
      - 自动同步 instrument config
      - pm2 友好的持续循环
    """

    # 各频率的默认回溯天数 (首次拉取)
    DEFAULT_LOOKBACK = {
        "daily": 365 * 5,
        "1min": 7,
        "5min": 30,
        "15min": 60,
        "30min": 60,
        "60min": 120,
    }

    def __init__(
        self,
        symbols: List[str],
        freqs: List[str] = None,
        client: XiximiaoClient = None,
        auto_sync_config: bool = True,
        initial_years: float = 5.0,
    ):
        self.symbols = symbols
        self.freqs = freqs or ["daily"]
        self.client = client or XiximiaoClient()
        self.auto_sync_config = auto_sync_config
        self.calendar = ChinaMarketCalendar

        # Stores (PG or Parquet depending on ASTOCK_BACKEND env)
        self._daily_store = get_daily_prices_store()
        self._minutes_store = get_minutes_prices_store()

        # Initial lookback override
        if initial_years != 5.0:
            self.DEFAULT_LOOKBACK["daily"] = int(365 * initial_years)

        # Stats
        self._running = False
        self._fetch_count = 0
        self._error_count = 0
        self._empty_count = 0
        self._last_fetch: Dict[str, datetime] = {}
        self._valid_symbols: List[str] = []

        logger.info("AStockFetcher initialized:")
        logger.info("  Universe: %d symbols", len(self.symbols))
        logger.info("  Frequencies: %s", self.freqs)
        logger.info("  Auto sync config: %s", self.auto_sync_config)
        logger.info("  Backend: %s", get_backend().value)

    # ── single fetch ───────────────────────────────────────────

    def fetch_symbol_daily(self, ts_code: str, force_start: datetime = None) -> int:
        """增量拉取日线。返回新增行数。"""
        latest = self._daily_store.get_latest_date(ts_code)
        now = datetime.now()

        if force_start:
            start = force_start
        elif latest:
            start = (latest - timedelta(days=3)).to_pydatetime()
        else:
            start = now - timedelta(days=self.DEFAULT_LOOKBACK["daily"])

        raw = self.client.fetch_daily_range(ts_code, start, now)
        if raw.empty:
            return 0

        df = _normalize_daily(raw)
        return self._daily_store.append_prices(ts_code, df)

    def fetch_symbol_minutes(
        self, ts_code: str, freq: str, force_start: datetime = None
    ) -> int:
        """增量拉取分钟线。返回新增行数。"""
        latest = self._minutes_store.get_latest_date(ts_code, freq)
        now = datetime.now()

        if force_start:
            start = force_start
        elif latest:
            start = (latest - timedelta(days=1)).to_pydatetime()
        else:
            lookback = self.DEFAULT_LOOKBACK.get(freq, 30)
            start = now - timedelta(days=lookback)

        raw = self.client.fetch_minutes_range(
            ts_code=ts_code, freq=freq, start=start, end=now
        )
        if raw.empty:
            return 0

        df = _normalize_minutes(raw)
        return self._minutes_store.append_prices(ts_code, freq, df)

    # ── batch fetch ────────────────────────────────────────────

    def fetch_all(self, show_progress: bool = True) -> Dict[str, int]:
        """拉取所有品种的所有频率。返回 {ts_code: new_rows} 统计。"""
        results = {}
        total = len(self.symbols) * len(self.freqs)
        done = 0
        batch_errors = 0
        batch_empty = 0

        for ts_code in self.symbols:
            total_new = 0
            is_valid = False

            for freq in self.freqs:
                try:
                    if freq == "daily":
                        n = self.fetch_symbol_daily(ts_code)
                    else:
                        n = self.fetch_symbol_minutes(ts_code, freq)
                    total_new += n
                    if n > 0:
                        is_valid = True
                    self._fetch_count += 1
                except Exception as e:
                    if "delisted" not in str(e).lower():
                        logger.debug("Error fetching %s %s: %s", ts_code, freq, e)
                    batch_errors += 1
                    self._error_count += 1

                done += 1
                if show_progress and done % 10 == 0:
                    pct = done / total * 100
                    logger.info(
                        "Progress: %d/%d (%.0f%%) — updated=%d errors=%d",
                        done, total, pct,
                        sum(1 for v in results.values() if v > 0),
                        batch_errors,
                    )

            if total_new == 0:
                batch_empty += 1
            else:
                results[ts_code] = total_new

            # 记录有效品种
            if is_valid or self._daily_store.get_latest_date(ts_code) is not None:
                self._valid_symbols.append(ts_code)

        loaded = sum(1 for v in results.values() if v > 0)
        logger.info(
            "Fetch complete: %d/%d updated, %d empty, %d errors",
            loaded, len(self.symbols), batch_empty, batch_errors,
        )

        # 更新有效品种列表
        if self._valid_symbols:
            unique_valid = sorted(set(self._valid_symbols))
            AStockUniverse.update_valid_symbols(unique_valid)
            logger.info("Valid symbols updated: %d total", len(unique_valid))

        # 自动同步 config
        if self.auto_sync_config and loaded > 0:
            sync_instrument_config(self._daily_store)

        return results

    # ── 全市场扫描 ─────────────────────────────────────────────

    def scan_market(self, batch_size: int = 100) -> List[str]:
        """
        全市场扫描：尝试拉取每个代码的最近10天日线，
        发现有数据的品种加入 valid_symbols.csv

        适合首次运行或定期刷新（发现新上市股票）

        Args:
            batch_size: 每批处理数量（日志用）

        Returns:
            有效品种列表
        """
        logger.info("=" * 60)
        logger.info("Starting full market scan: %d codes to check", len(self.symbols))
        logger.info("=" * 60)

        valid = []
        now = datetime.now()
        start = now - timedelta(days=30)

        for i, ts_code in enumerate(self.symbols):
            try:
                raw = self.client.fetch_daily_range(ts_code, start, now)
                if not raw.empty and len(raw) >= 1:
                    valid.append(ts_code)
            except Exception:
                pass

            if (i + 1) % batch_size == 0:
                logger.info(
                    "Scan progress: %d/%d checked, %d valid found",
                    i + 1, len(self.symbols), len(valid),
                )

        logger.info("Scan complete: %d/%d valid", len(valid), len(self.symbols))

        # 保存有效品种
        AStockUniverse.save_valid_symbols(valid)

        return valid

    # ── scheduled loop ─────────────────────────────────────────

    def run_loop(self, force: bool = False):
        """
        持续运行的调度循环

        - 交易日 fetch window (9:00-15:30) 内持续拉取
        - 非交易时间智能休眠
        - 每天收盘后做一次完整日线刷新
        - 支持 force 模式忽略交易时间
        """
        logger.info("=" * 60)
        logger.info("AStockFetcher loop starting")
        logger.info("  Symbols: %d, Freqs: %s", len(self.symbols), self.freqs)
        logger.info("  Force mode: %s", force)
        logger.info("=" * 60)

        self._running = True
        daily_done_today = False

        while self._running:
            try:
                status = self.calendar.get_status()
                logger.info("Market: %s", status.get("status", "UNKNOWN"))

                should_fetch = force or self.calendar.is_fetch_window()

                # 每天日期变化时重置标记
                today = datetime.now().date()
                if hasattr(self, '_last_date') and self._last_date != today:
                    daily_done_today = False
                self._last_date = today

                if should_fetch:
                    # 交易窗口内拉取
                    results = self.fetch_all(show_progress=True)
                    total_new = sum(results.values())
                    logger.info("Fetched %d new rows", total_new)

                    # 收盘后标记日线已完成
                    now_time = datetime.now().time()
                    from datetime import time as dt_time
                    if now_time >= dt_time(15, 5):
                        daily_done_today = True
                        logger.info("Post-close daily fetch done for today")

                    # 计算休眠
                    sleep_sec = self.calendar.get_sleep_seconds(self.freqs)
                    logger.info("Next fetch in %ds", sleep_sec)
                    time.sleep(sleep_sec)

                else:
                    # 非交易窗口
                    sleep_sec = self.calendar.get_sleep_seconds(self.freqs)

                    if "time_to_open" in status:
                        logger.info(
                            "Sleeping %ds (next open: %s)",
                            sleep_sec, status.get("time_to_open"),
                        )
                    elif "next_trading_day" in status:
                        logger.info(
                            "Sleeping %ds (next trading day: %s)",
                            sleep_sec, status.get("next_trading_day"),
                        )
                    else:
                        logger.info("Sleeping %ds", sleep_sec)

                    time.sleep(sleep_sec)

            except KeyboardInterrupt:
                logger.info("Interrupted — stopping")
                self._running = False
            except Exception as e:
                logger.error("Loop error: %s", e, exc_info=True)
                self._error_count += 1
                time.sleep(60)

        self._print_stats()

    def stop(self):
        """停止服务"""
        self._running = False

    # ── stats ──────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "symbols": len(self.symbols),
            "freqs": self.freqs,
            "fetch_count": self._fetch_count,
            "error_count": self._error_count,
            "empty_count": self._empty_count,
            "last_fetch": {k: v.isoformat() for k, v in self._last_fetch.items()},
            "valid_symbols": len(self._valid_symbols),
            "market_status": self.calendar.get_status(),
        }

    def _print_stats(self):
        stats = self.get_stats()
        logger.info("=" * 40)
        logger.info("Fetcher Stats:")
        for k, v in stats.items():
            logger.info("  %s: %s", k, v)
        logger.info("=" * 40)


# ── 数据信息 ────────────────────────────────────────────────────

def show_data_info():
    """显示已存储的数据统计"""
    backend = get_backend()
    daily = get_daily_prices_store()
    mins = get_minutes_prices_store()

    instruments = daily.get_list_of_instruments()
    print(f"\n{'='*50}")
    print(f"A-Stock Data Info (backend: {backend.value})")
    print(f"{'='*50}")
    print(f"Daily instruments: {len(instruments)}")

    if instruments:
        sample = instruments[:5] + instruments[-2:] if len(instruments) > 7 else instruments
        print(f"\nSample instruments (daily):")
        for code in sample:
            prices = daily.get_prices(code)
            if not prices.empty:
                print(f"  {code}: {len(prices)} bars, "
                      f"{prices.index[0].date()} ~ {prices.index[-1].date()}")

    # 分钟数据
    for freq in ["1min", "5min", "15min", "30min", "60min"]:
        instr = mins.get_list_of_instruments(freq)
        if instr:
            print(f"\n{freq} instruments: {len(instr)}")

    # Valid symbols
    valid = AStockUniverse.load_valid_symbols()
    print(f"\nValid symbols: {len(valid)}")

    # Config — backend-aware
    if is_pg_enabled():
        instr_store = get_instrument_data_store()
        spread_store = get_spread_cost_store()
        print(f"Instrument config (PG): {len(instr_store.get_list_of_instruments())} entries")
        print(f"Spread costs (PG): {len(spread_store.get_list_of_instruments())} entries")
    else:
        config_file = CONFIG_DIR / "instrumentconfig.csv"
        spread_file = CONFIG_DIR / "spreadcosts.csv"
        if config_file.exists():
            df = pd.read_csv(config_file)
            print(f"Instrument config (CSV): {len(df)} entries")
        if spread_file.exists():
            df = pd.read_csv(spread_file)
            print(f"Spread costs (CSV): {len(df)} entries")

        parquet_dir = REPO_ROOT / "data" / "astock"
        total_size = sum(f.stat().st_size for f in parquet_dir.rglob("*.parquet"))
        print(f"\nParquet disk usage: {total_size / 1024 / 1024:.1f} MB")

    print(f"{'='*50}")


# ── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="A-stock data fetcher — 全市场定时调度增量拉取",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 一次性拉取热门股日线
  %(prog)s --once --freq daily --universe popular

  # 全市场扫描发现有效品种
  %(prog)s --scan --universe full

  # 持续运行 (pm2 管理)
  %(prog)s --freq daily --universe valid

  # 查看状态
  %(prog)s --status
  %(prog)s --info
        """,
    )

    parser.add_argument(
        "--universe", type=str, default="popular",
        help="Stock universe: " + ", ".join(AStockUniverse.available_pools()),
    )
    parser.add_argument(
        "--symbols", nargs="+", default=None,
        help="Specific symbols (overrides --universe)",
    )
    parser.add_argument(
        "--freq", nargs="+", default=["daily"],
        help="Frequencies: daily 1min 5min 15min 30min 60min",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run once and exit",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force fetch (ignore market hours)",
    )
    parser.add_argument(
        "--scan", action="store_true",
        help="Scan market for valid symbols",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show market status and exit",
    )
    parser.add_argument(
        "--info", action="store_true",
        help="Show data info and exit",
    )
    parser.add_argument(
        "--sync-config", action="store_true",
        help="Sync instrument config from stored data",
    )
    parser.add_argument(
        "--years", type=float, default=5.0,
        help="Initial history lookback in years for daily (default: 5)",
    )
    parser.add_argument(
        "--lookback-days", type=int, default=None,
        help="Override lookback days for all frequencies",
    )
    parser.add_argument(
        "--no-sync", action="store_true",
        help="Disable auto config sync",
    )
    parser.add_argument(
        "--backend", type=str, default=None,
        choices=["parquet", "pg"],
        help="Override data backend (default: from ASTOCK_BACKEND env)",
    )

    args = parser.parse_args()

    # ── backend override ──────────────────────────────────────
    if args.backend:
        import os
        os.environ["ASTOCK_BACKEND"] = args.backend
        logger.info("Backend override: %s", args.backend)

    # ── info commands ──────────────────────────────────────────

    if args.status:
        status = ChinaMarketCalendar.get_status()
        print("\nA股市场状态:")
        for k, v in status.items():
            print(f"  {k}: {v}")

        print(f"\n数据后端: {get_backend().value}")

        print(f"\n股票池:")
        for pool in AStockUniverse.available_pools():
            symbols = AStockUniverse.get(pool)
            print(f"  {pool}: {len(symbols)} 只")
        return

    if args.info:
        show_data_info()
        return

    if args.sync_config:
        daily_store = get_daily_prices_store()
        sync_instrument_config(daily_store)
        return

    # ── resolve symbols ────────────────────────────────────────

    symbols = args.symbols or AStockUniverse.get(args.universe)
    logger.info("Universe: %s, Symbols: %d, Freqs: %s",
                args.universe, len(symbols), args.freq)

    # ── build fetcher ──────────────────────────────────────────

    fetcher = AStockFetcher(
        symbols=symbols,
        freqs=args.freq,
        auto_sync_config=not args.no_sync,
        initial_years=args.years,
    )

    if args.lookback_days:
        for freq in args.freq:
            AStockFetcher.DEFAULT_LOOKBACK[freq] = args.lookback_days

    # ── execute ────────────────────────────────────────────────

    if args.scan:
        valid = fetcher.scan_market()
        logger.info("Found %d valid symbols", len(valid))
        return

    if args.once or args.force:
        if args.force and not args.once:
            # --force without --once: force one round then loop
            logger.info("Force-fetching one round...")
            results = fetcher.fetch_all()
            total = sum(results.values())
            logger.info("Force round: %d new rows", total)
            # Then enter normal loop
            fetcher.run_loop(force=False)
        else:
            results = fetcher.fetch_all()
            total = sum(results.values())
            logger.info("Total new rows: %d", total)
    else:
        fetcher.run_loop(force=False)


if __name__ == "__main__":
    main()
