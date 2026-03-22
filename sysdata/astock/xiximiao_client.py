"""
XiximiaoClient - A股数据 API 客户端

通过 xiximiao.com 代理（Tushare 兼容）获取 A股行情数据。
支持分页、限流、自动重试。

接口:
    - stk_mins: 历史分钟行情 (1/5/15/30/60min)
    - daily:    历史日线行情

关键限制:
    - stk_mins 单次最大 8000 行, offset 最大 100000
    - 需注意 start_date / end_date 间隔不要导致总行数溢出
"""

import os
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Load .env from repo root if python-dotenv is available
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(_ENV_FILE)
except ImportError:
    pass  # python-dotenv is optional; user can set env vars manually

DEFAULT_TOKEN = os.environ.get("XIXIMIAO_TOKEN", "")
DEFAULT_API_URL = os.environ.get(
    "XIXIMIAO_API_URL", "http://stk_mins.xiximiao.com/dataapi"
)
MAX_ROWS_PER_CALL = 8000
MAX_OFFSET = 100000
RATE_LIMIT_SLEEP = 0.35
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0


def _init_pro(token: str = DEFAULT_TOKEN, api_url: str = DEFAULT_API_URL):
    import tushare as ts

    pro = ts.pro_api(token="placeholder")
    pro._DataApi__token = token
    pro._DataApi__http_url = api_url
    return pro


class XiximiaoClient:
    """
    xiximiao A股数据客户端

    封装分页逻辑、限流和重试。
    """

    FREQ_MAP = {
        "1min": "1min",
        "5min": "5min",
        "15min": "15min",
        "30min": "30min",
        "60min": "60min",
    }

    def __init__(
        self,
        token: str = DEFAULT_TOKEN,
        api_url: str = DEFAULT_API_URL,
        rate_limit: float = RATE_LIMIT_SLEEP,
    ):
        self._pro = _init_pro(token, api_url)
        self._rate_limit = rate_limit
        self._last_call_time = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_call_time
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)
        self._last_call_time = time.time()

    def _call_with_retry(self, fn, **kwargs) -> Optional[pd.DataFrame]:
        for attempt in range(MAX_RETRIES):
            try:
                self._throttle()
                df = fn(**kwargs)
                return df
            except Exception as e:
                wait = RETRY_BACKOFF ** (attempt + 1)
                logger.warning(
                    "API call failed (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1,
                    MAX_RETRIES,
                    e,
                    wait,
                )
                time.sleep(wait)
        logger.error("API call failed after %d retries", MAX_RETRIES)
        return None

    # ── daily ──────────────────────────────────────────────────

    def fetch_daily(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        获取日线数据

        Args:
            ts_code:    '600000.SH'
            start_date: '20240101'
            end_date:   '20241231'

        Returns:
            DataFrame with columns: ts_code, trade_date, open, high, low, close,
                                    pre_close, change, pct_chg, vol, amount
        """
        df = self._call_with_retry(
            self._pro.daily,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        if df is None or df.empty:
            return pd.DataFrame()
        return df.sort_values("trade_date").reset_index(drop=True)

    # ── stk_mins ───────────────────────────────────────────────

    def fetch_minutes(
        self,
        ts_code: str,
        freq: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        获取分钟线数据（自动分页拼接）

        Args:
            ts_code:    '600000.SH'
            freq:       '1min' / '5min' / '15min' / '30min' / '60min'
            start_date: '2025-03-17 09:00:00'
            end_date:   '2025-03-17 15:00:00'

        Returns:
            DataFrame with columns: ts_code, trade_time, open, high, low, close, vol, amount
        """
        all_chunks: List[pd.DataFrame] = []
        offset = 0

        while offset <= MAX_OFFSET:
            df = self._call_with_retry(
                self._pro.stk_mins,
                ts_code=ts_code,
                freq=freq,
                start_date=start_date,
                end_date=end_date,
                limit=MAX_ROWS_PER_CALL,
                offset=offset,
            )

            if df is None or df.empty:
                break

            all_chunks.append(df)

            if len(df) < MAX_ROWS_PER_CALL:
                break

            offset += MAX_ROWS_PER_CALL
            logger.info(
                "Paginating %s %s: offset=%d, got %d rows so far",
                ts_code,
                freq,
                offset,
                sum(len(c) for c in all_chunks),
            )

        if not all_chunks:
            return pd.DataFrame()

        result = pd.concat(all_chunks, ignore_index=True)
        result = result.drop_duplicates(subset=["trade_time"], keep="last")
        result = result.sort_values("trade_time").reset_index(drop=True)
        return result

    # ── batch helpers ──────────────────────────────────────────

    def fetch_daily_range(
        self,
        ts_code: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """便捷方法：datetime 入参"""
        return self.fetch_daily(
            ts_code=ts_code,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )

    def fetch_minutes_range(
        self,
        ts_code: str,
        freq: str,
        start: datetime,
        end: datetime,
        chunk_days: int = 5,
    ) -> pd.DataFrame:
        """
        按天窗口分批拉取分钟数据，避免单次请求行数溢出。
        chunk_days: 每批覆盖的天数（默认5天）
        """
        all_chunks: List[pd.DataFrame] = []
        chunk_start = start

        while chunk_start < end:
            chunk_end = min(chunk_start + timedelta(days=chunk_days), end)
            s = chunk_start.strftime("%Y-%m-%d %H:%M:%S")
            e = chunk_end.strftime("%Y-%m-%d %H:%M:%S")

            df = self.fetch_minutes(ts_code=ts_code, freq=freq, start_date=s, end_date=e)
            if not df.empty:
                all_chunks.append(df)

            chunk_start = chunk_end

        if not all_chunks:
            return pd.DataFrame()

        result = pd.concat(all_chunks, ignore_index=True)
        result = result.drop_duplicates(subset=["trade_time"], keep="last")
        result = result.sort_values("trade_time").reset_index(drop=True)
        return result
