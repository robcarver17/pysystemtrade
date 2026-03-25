"""
ChinaMarketCalendar - A股交易日历

检测A股开盘时间，提供交易日判断、距开盘/收盘时间等。
用于 fetcher 调度决策。

参考: LocalTradeSystem/online_system/data/china_calendar.py
"""

from datetime import datetime, time, timedelta
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

try:
    import pytz
    SHANGHAI_TZ = pytz.timezone('Asia/Shanghai')
except ImportError:
    SHANGHAI_TZ = None


class ChinaMarketCalendar:
    """
    A股交易日历

    交易时间 (北京时间):
    - 上午: 9:30 - 11:30
    - 下午: 13:00 - 15:00
    - 集合竞价: 9:15 - 9:25 (开盘), 14:57 - 15:00 (收盘)

    休市日:
    - 周末（周六、周日）
    - 法定节假日（元旦、春节、清明、劳动节、端午、中秋、国庆）
    """

    # 交易时间
    MORNING_OPEN = time(9, 30)
    MORNING_CLOSE = time(11, 30)
    AFTERNOON_OPEN = time(13, 0)
    AFTERNOON_CLOSE = time(15, 0)

    # 集合竞价
    AUCTION_START = time(9, 15)
    CLOSE_AUCTION_START = time(14, 57)

    # fetcher 活跃窗口 (比交易时间略宽)
    FETCH_WINDOW_START = time(9, 0)
    FETCH_WINDOW_END = time(15, 30)

    # 2024-2027 A股休市日（法定节假日 + 调休）
    HOLIDAYS = {
        # 2024
        datetime(2024, 1, 1),
        datetime(2024, 2, 10), datetime(2024, 2, 11), datetime(2024, 2, 12),
        datetime(2024, 2, 13), datetime(2024, 2, 14), datetime(2024, 2, 15),
        datetime(2024, 2, 16), datetime(2024, 2, 17),
        datetime(2024, 4, 4), datetime(2024, 4, 5), datetime(2024, 4, 6),
        datetime(2024, 5, 1), datetime(2024, 5, 2), datetime(2024, 5, 3),
        datetime(2024, 5, 4), datetime(2024, 5, 5),
        datetime(2024, 6, 8), datetime(2024, 6, 9), datetime(2024, 6, 10),
        datetime(2024, 9, 15), datetime(2024, 9, 16), datetime(2024, 9, 17),
        datetime(2024, 10, 1), datetime(2024, 10, 2), datetime(2024, 10, 3),
        datetime(2024, 10, 4), datetime(2024, 10, 5), datetime(2024, 10, 6),
        datetime(2024, 10, 7),

        # 2025
        datetime(2025, 1, 1),
        datetime(2025, 1, 28), datetime(2025, 1, 29), datetime(2025, 1, 30),
        datetime(2025, 1, 31), datetime(2025, 2, 1), datetime(2025, 2, 2),
        datetime(2025, 2, 3), datetime(2025, 2, 4),
        datetime(2025, 4, 4), datetime(2025, 4, 5), datetime(2025, 4, 6),
        datetime(2025, 5, 1), datetime(2025, 5, 2), datetime(2025, 5, 3),
        datetime(2025, 5, 4), datetime(2025, 5, 5),
        datetime(2025, 5, 31), datetime(2025, 6, 1), datetime(2025, 6, 2),
        datetime(2025, 10, 1), datetime(2025, 10, 2), datetime(2025, 10, 3),
        datetime(2025, 10, 4), datetime(2025, 10, 5), datetime(2025, 10, 6),
        datetime(2025, 10, 7), datetime(2025, 10, 8),

        # 2026
        datetime(2026, 1, 1), datetime(2026, 1, 2),
        datetime(2026, 2, 17), datetime(2026, 2, 18), datetime(2026, 2, 19),
        datetime(2026, 2, 20), datetime(2026, 2, 21), datetime(2026, 2, 22),
        datetime(2026, 2, 23),
        datetime(2026, 4, 5), datetime(2026, 4, 6), datetime(2026, 4, 7),
        datetime(2026, 5, 1), datetime(2026, 5, 2), datetime(2026, 5, 3),
        datetime(2026, 6, 19), datetime(2026, 6, 20), datetime(2026, 6, 21),
        datetime(2026, 10, 1), datetime(2026, 10, 2), datetime(2026, 10, 3),
        datetime(2026, 10, 4), datetime(2026, 10, 5), datetime(2026, 10, 6),
        datetime(2026, 10, 7), datetime(2026, 10, 8),

        # 2027 (预估，需要每年更新)
        datetime(2027, 1, 1),
        datetime(2027, 2, 6), datetime(2027, 2, 7), datetime(2027, 2, 8),
        datetime(2027, 2, 9), datetime(2027, 2, 10), datetime(2027, 2, 11),
        datetime(2027, 2, 12),
        datetime(2027, 4, 5), datetime(2027, 4, 6),
        datetime(2027, 5, 1), datetime(2027, 5, 2), datetime(2027, 5, 3),
        datetime(2027, 6, 8), datetime(2027, 6, 9),
        datetime(2027, 10, 1), datetime(2027, 10, 2), datetime(2027, 10, 3),
        datetime(2027, 10, 4), datetime(2027, 10, 5), datetime(2027, 10, 6),
        datetime(2027, 10, 7),
    }

    @classmethod
    def now_cn(cls) -> datetime:
        """获取当前北京时间"""
        if SHANGHAI_TZ is not None:
            return datetime.now(SHANGHAI_TZ).replace(tzinfo=None)
        # 如果没有 pytz，假设系统已是中国时区
        return datetime.now()

    @classmethod
    def is_holiday(cls, dt: datetime = None) -> bool:
        """是否是节假日"""
        dt = dt or cls.now_cn()
        date_only = datetime(dt.year, dt.month, dt.day)
        return date_only in cls.HOLIDAYS

    @classmethod
    def is_weekend(cls, dt: datetime = None) -> bool:
        """是否是周末"""
        dt = dt or cls.now_cn()
        return dt.weekday() >= 5

    @classmethod
    def is_trading_day(cls, dt: datetime = None) -> bool:
        """是否是交易日"""
        dt = dt or cls.now_cn()
        return not cls.is_weekend(dt) and not cls.is_holiday(dt)

    @classmethod
    def is_market_open(cls, dt: datetime = None) -> bool:
        """当前是否在交易时间内"""
        dt = dt or cls.now_cn()
        if not cls.is_trading_day(dt):
            return False
        t = dt.time()
        morning = cls.MORNING_OPEN <= t <= cls.MORNING_CLOSE
        afternoon = cls.AFTERNOON_OPEN <= t <= cls.AFTERNOON_CLOSE
        return morning or afternoon

    @classmethod
    def is_fetch_window(cls, dt: datetime = None) -> bool:
        """
        当前是否在 fetcher 活跃窗口

        比交易时间宽：9:00 - 15:30，让 fetcher 提前和延后运行
        """
        dt = dt or cls.now_cn()
        if not cls.is_trading_day(dt):
            return False
        t = dt.time()
        return cls.FETCH_WINDOW_START <= t <= cls.FETCH_WINDOW_END

    @classmethod
    def time_to_open(cls, dt: datetime = None) -> Optional[timedelta]:
        """距下次开盘的时间"""
        dt = dt or cls.now_cn()
        # 找到下一个交易日
        target = dt
        for _ in range(10):
            if cls.is_trading_day(target):
                open_dt = datetime.combine(target.date(), cls.MORNING_OPEN)
                if open_dt > dt:
                    return open_dt - dt
            target = target + timedelta(days=1)
            target = datetime.combine(target.date(), time(0, 0))
        return None

    @classmethod
    def time_to_close(cls, dt: datetime = None) -> Optional[timedelta]:
        """距今日收盘的时间"""
        dt = dt or cls.now_cn()
        if not cls.is_trading_day(dt):
            return None
        close_dt = datetime.combine(dt.date(), cls.AFTERNOON_CLOSE)
        if close_dt > dt:
            return close_dt - dt
        return None

    @classmethod
    def next_trading_day(cls, dt: datetime = None) -> datetime:
        """下一个交易日"""
        dt = dt or cls.now_cn()
        target = dt + timedelta(days=1)
        for _ in range(30):
            if cls.is_trading_day(target):
                return target
            target += timedelta(days=1)
        return target

    @classmethod
    def get_status(cls, dt: datetime = None) -> Dict:
        """获取完整市场状态"""
        dt = dt or cls.now_cn()
        is_open = cls.is_market_open(dt)
        is_trading = cls.is_trading_day(dt)

        status = {
            'time': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'is_trading_day': is_trading,
            'is_market_open': is_open,
            'is_fetch_window': cls.is_fetch_window(dt),
        }

        if is_open:
            status['status'] = 'OPEN'
            ttc = cls.time_to_close(dt)
            if ttc:
                status['time_to_close'] = str(ttc).split('.')[0]
        elif is_trading and dt.time() < cls.MORNING_OPEN:
            status['status'] = 'PRE_MARKET'
            tto = cls.time_to_open(dt)
            if tto:
                status['time_to_open'] = str(tto).split('.')[0]
        elif is_trading and dt.time() > cls.AFTERNOON_CLOSE:
            status['status'] = 'CLOSED_TODAY'
            nxt = cls.next_trading_day(dt)
            status['next_trading_day'] = nxt.strftime('%Y-%m-%d')
        elif is_trading and cls.MORNING_CLOSE < dt.time() < cls.AFTERNOON_OPEN:
            status['status'] = 'LUNCH_BREAK'
            status['afternoon_open'] = cls.AFTERNOON_OPEN.strftime('%H:%M')
        else:
            status['status'] = 'CLOSED'
            if cls.is_weekend(dt):
                status['reason'] = 'weekend'
            elif cls.is_holiday(dt):
                status['reason'] = 'holiday'
            tto = cls.time_to_open(dt)
            if tto:
                status['time_to_open'] = str(tto).split('.')[0]
            nxt = cls.next_trading_day(dt)
            status['next_trading_day'] = nxt.strftime('%Y-%m-%d')

        return status

    @classmethod
    def get_sleep_seconds(cls, freqs: list = None, dt: datetime = None) -> int:
        """
        根据当前状态和频率返回建议休眠秒数

        供 fetcher 主循环使用
        """
        dt = dt or cls.now_cn()

        FREQ_INTERVALS = {
            'daily': 3600,
            '1min': 60,
            '5min': 120,
            '15min': 300,
            '30min': 300,
            '60min': 600,
        }

        if cls.is_fetch_window(dt):
            if freqs:
                return min(FREQ_INTERVALS.get(f, 300) for f in freqs)
            return 300

        # 非交易窗口
        tto = cls.time_to_open(dt)
        if tto:
            secs = int(tto.total_seconds())
            if secs < 600:
                return max(secs, 10)
            # 距开盘较远，按较长间隔检查
            return min(secs, 1800)

        return 1800  # 默认半小时


if __name__ == "__main__":
    status = ChinaMarketCalendar.get_status()
    print("A股市场状态:")
    for k, v in status.items():
        print(f"  {k}: {v}")
