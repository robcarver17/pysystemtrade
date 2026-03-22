"""
A-stock data fetcher — 定时调度增量拉取

从 xiximiao API 拉取 A股日线/分钟线数据，存入 Parquet。
支持增量更新（只拉新数据）、多品种并行、定时调度循环。

用法:
    # 一次性拉取
    python -m sysinit.astock.fetcher --once --freq daily --universe sse50

    # 持续运行 (适合 cron / pm2)
    python -m sysinit.astock.fetcher --freq daily 5min --universe popular

    # 指定品种
    python -m sysinit.astock.fetcher --once --freq daily --symbols 600519.SH 000858.SZ
"""

import argparse
import logging
import time
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from sysdata.astock.xiximiao_client import XiximiaoClient
from sysdata.astock.astock_prices import AStockDailyPricesData, AStockMinutesPricesData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("astock.fetcher")


# ── 股票池 ──────────────────────────────────────────────────────

UNIVERSES = {
    "sse50": [
        "600000.SH", "600009.SH", "600010.SH", "600011.SH", "600015.SH",
        "600016.SH", "600018.SH", "600019.SH", "600025.SH", "600028.SH",
        "600030.SH", "600031.SH", "600036.SH", "600048.SH", "600050.SH",
        "600089.SH", "600104.SH", "600111.SH", "600150.SH", "600176.SH",
        "600196.SH", "600276.SH", "600309.SH", "600406.SH", "600436.SH",
        "600438.SH", "600519.SH", "600585.SH", "600588.SH", "600690.SH",
        "600745.SH", "600809.SH", "600887.SH", "600893.SH", "600900.SH",
        "600905.SH", "601012.SH", "601066.SH", "601088.SH", "601138.SH",
        "601166.SH", "601225.SH", "601288.SH", "601318.SH", "601390.SH",
        "601398.SH", "601601.SH", "601628.SH", "601668.SH", "601857.SH",
    ],
    "popular": [
        "600519.SH", "000858.SZ", "600036.SH", "601318.SH", "000333.SZ",
        "000651.SZ", "600887.SH", "002415.SZ", "600276.SH", "300750.SZ",
        "002594.SZ", "688981.SH", "002230.SZ", "300059.SZ", "600703.SH",
        "002475.SZ", "300124.SZ", "688041.SH", "601398.SH", "601288.SH",
        "600030.SH", "601166.SH", "600690.SH", "000568.SZ", "600809.SH",
        "002304.SZ", "601857.SH", "600028.SH", "601088.SH", "600900.SH",
    ],
    "index_etf": [
        "510050.SH", "510300.SH", "510330.SH", "510500.SH", "512100.SH",
        "159915.SZ", "159919.SZ",
    ],
    "test": [
        "600519.SH", "000858.SZ", "600036.SH",
    ],
}


def get_universe(name: str) -> List[str]:
    return UNIVERSES.get(name.lower(), UNIVERSES["test"])


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


# ── Fetcher ─────────────────────────────────────────────────────

class AStockFetcher:
    """
    A股数据拉取器

    功能:
      - 增量拉取日线/分钟线
      - 多品种串行（限流友好）
      - 可一次性运行或持续循环
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

    # 循环刷新间隔 (秒)
    REFRESH_INTERVALS = {
        "daily": 3600,       # 1小时
        "1min": 60,
        "5min": 120,
        "15min": 300,
        "30min": 300,
        "60min": 600,
    }

    def __init__(
        self,
        symbols: List[str],
        freqs: List[str] = None,
        client: XiximiaoClient = None,
    ):
        self.symbols = symbols
        self.freqs = freqs or ["daily"]
        self.client = client or XiximiaoClient()

        # Stores
        self._daily_store = AStockDailyPricesData()
        self._minutes_store = AStockMinutesPricesData()

        # Stats
        self._fetch_count = 0
        self._error_count = 0
        self._last_fetch: Dict[str, datetime] = {}

    # ── single fetch ───────────────────────────────────────────

    def fetch_symbol_daily(self, ts_code: str, force_start: datetime = None) -> int:
        """
        增量拉取日线。返回新增行数。
        """
        latest = self._daily_store.get_latest_date(ts_code)
        now = datetime.now()

        if force_start:
            start = force_start
        elif latest:
            start = (latest - timedelta(days=3)).to_pydatetime()  # 多取几天防漏
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

        for ts_code in self.symbols:
            total_new = 0
            for freq in self.freqs:
                try:
                    if freq == "daily":
                        n = self.fetch_symbol_daily(ts_code)
                    else:
                        n = self.fetch_symbol_minutes(ts_code, freq)
                    total_new += n
                    self._fetch_count += 1
                except Exception as e:
                    logger.error("Error fetching %s %s: %s", ts_code, freq, e)
                    self._error_count += 1
                done += 1
                if show_progress and done % 5 == 0:
                    logger.info("Progress: %d/%d", done, total)

            results[ts_code] = total_new

        loaded = sum(1 for v in results.values() if v > 0)
        logger.info(
            "Fetch complete: %d/%d symbols updated, %d errors",
            loaded,
            len(self.symbols),
            self._error_count,
        )
        return results

    # ── scheduled loop ─────────────────────────────────────────

    def run_loop(self):
        """持续运行的调度循环"""
        logger.info("=" * 60)
        logger.info("AStockFetcher starting — %d symbols, freqs=%s",
                     len(self.symbols), self.freqs)
        logger.info("=" * 60)

        while True:
            try:
                # 判断当前是否在 A股交易时间附近 (北京时间 9:00-16:00 工作日)
                now = datetime.now()
                hour = now.hour
                weekday = now.weekday()

                if weekday >= 5:
                    # 周末，长睡眠
                    logger.info("Weekend — sleeping 4h")
                    time.sleep(4 * 3600)
                    continue

                if hour < 9 or hour >= 16:
                    # 非交易时间
                    sleep_sec = 1800
                    logger.info("Off-hours (hour=%d) — sleeping %ds", hour, sleep_sec)
                    time.sleep(sleep_sec)
                    continue

                # 交易时间，执行拉取
                results = self.fetch_all(show_progress=False)
                total_new = sum(results.values())
                logger.info("Fetched %d new rows across %d symbols",
                           total_new, len(self.symbols))

                # 按最小频率决定休眠
                min_interval = min(
                    self.REFRESH_INTERVALS.get(f, 300) for f in self.freqs
                )
                logger.info("Next refresh in %ds", min_interval)
                time.sleep(min_interval)

            except KeyboardInterrupt:
                logger.info("Interrupted — stopping")
                break
            except Exception as e:
                logger.error("Loop error: %s", e)
                time.sleep(60)

    # ── stats ──────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "symbols": len(self.symbols),
            "freqs": self.freqs,
            "fetch_count": self._fetch_count,
            "error_count": self._error_count,
        }


# ── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="A-stock data fetcher")
    parser.add_argument(
        "--universe", type=str, default="test",
        choices=list(UNIVERSES.keys()),
        help="Stock universe",
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
        "--lookback-days", type=int, default=None,
        help="Override default lookback for initial fetch",
    )

    args = parser.parse_args()

    symbols = args.symbols or get_universe(args.universe)
    logger.info("Symbols: %d, Freqs: %s", len(symbols), args.freq)

    fetcher = AStockFetcher(symbols=symbols, freqs=args.freq)

    if args.lookback_days:
        for freq in args.freq:
            AStockFetcher.DEFAULT_LOOKBACK[freq] = args.lookback_days

    if args.once:
        results = fetcher.fetch_all()
        total = sum(results.values())
        logger.info("Total new rows: %d", total)
    else:
        fetcher.run_loop()


if __name__ == "__main__":
    main()
