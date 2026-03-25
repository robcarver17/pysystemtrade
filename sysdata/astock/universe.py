"""
AStockUniverse - A股全市场股票池管理

提供A股预定义股票池及动态管理：
- SSE50:   上证50
- HS300:   沪深300核心成分
- ZZ500:   中证500核心成分
- ZZ1000:  中证1000部分成分
- POPULAR: 热门交易标的
- ETF:     常用ETF
- ALL:     全部去重合集
- FULL_MARKET: 全市场主板+创业板+科创板

代码格式: 600000.SH (上海), 000001.SZ (深圳)

参考: LocalTradeSystem/online_system/data/cn_universe.py
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class AStockUniverse:
    """
    A股股票池管理器

    支持:
    - 预定义池（静态列表）
    - 全市场池（从本地 csv 加载，可定期更新）
    - 自定义池（用户指定 symbols）
    - 行业/板块筛选
    """

    # ── 上证50 ──────────────────────────────────────────────────
    SSE50 = [
        '600000.SH', '600009.SH', '600010.SH', '600011.SH', '600015.SH',
        '600016.SH', '600018.SH', '600019.SH', '600025.SH', '600028.SH',
        '600030.SH', '600031.SH', '600036.SH', '600048.SH', '600050.SH',
        '600089.SH', '600104.SH', '600111.SH', '600150.SH', '600176.SH',
        '600196.SH', '600276.SH', '600309.SH', '600406.SH', '600436.SH',
        '600438.SH', '600519.SH', '600585.SH', '600588.SH', '600690.SH',
        '600745.SH', '600809.SH', '600887.SH', '600893.SH', '600900.SH',
        '600905.SH', '601012.SH', '601066.SH', '601088.SH', '601138.SH',
        '601166.SH', '601225.SH', '601288.SH', '601318.SH', '601390.SH',
        '601398.SH', '601601.SH', '601628.SH', '601668.SH', '601857.SH',
    ]

    # ── 沪深300 核心成分（约100只高权重股）────────────────────────
    HS300_CORE = [
        # 金融
        '601318.SH', '600036.SH', '601166.SH', '600030.SH', '601398.SH',
        '601288.SH', '601328.SH', '601601.SH', '601628.SH', '601988.SH',
        '601319.SH', '601818.SH', '600016.SH', '600000.SH', '000001.SZ',
        '000002.SZ', '002142.SZ', '300059.SZ',
        # 消费
        '600519.SH', '000858.SZ', '600887.SH', '603259.SH', '000568.SZ',
        '600809.SH', '002304.SZ', '600132.SH', '000333.SZ', '000651.SZ',
        '600690.SH', '002714.SZ',
        # 科技
        '002415.SZ', '600703.SH', '601138.SH', '002230.SZ', '300750.SZ',
        '002475.SZ', '688981.SH', '688041.SH', '002371.SZ', '300014.SZ',
        '002236.SZ', '300124.SZ',
        # 医药
        '600276.SH', '000538.SZ', '300760.SZ', '600196.SH', '002007.SZ',
        '300122.SZ', '300015.SZ', '600436.SH',
        # 新能源
        '002594.SZ', '601012.SH', '600438.SH', '002459.SZ',
        '300274.SZ', '601615.SH',
        # 工业/材料
        '600031.SH', '000625.SZ', '601225.SH', '600019.SH', '600585.SH',
        '601899.SH', '000786.SZ',
        # 地产/基建
        '600048.SH', '001979.SZ', '600383.SH', '601668.SH', '601390.SH',
        # 通信/互联网
        '600050.SH', '601728.SH', '600941.SH',
        # 能源
        '601857.SH', '600028.SH', '601088.SH', '600900.SH', '600905.SH',
    ]

    # ── 中证500 核心成分（部分）──────────────────────────────────
    ZZ500_CORE = [
        '000063.SZ', '000100.SZ', '000157.SZ', '000301.SZ', '000338.SZ',
        '000408.SZ', '000425.SZ', '000513.SZ', '000519.SZ', '000528.SZ',
        '000536.SZ', '000547.SZ', '000559.SZ', '000581.SZ', '000596.SZ',
        '000617.SZ', '000630.SZ', '000636.SZ', '000656.SZ', '000681.SZ',
        '000703.SZ', '000708.SZ', '000717.SZ', '000723.SZ', '000725.SZ',
        '000728.SZ', '000733.SZ', '000738.SZ', '000739.SZ', '000768.SZ',
        '000778.SZ', '000783.SZ', '000800.SZ', '000807.SZ', '000830.SZ',
        '000876.SZ', '000895.SZ', '000898.SZ', '000937.SZ', '000958.SZ',
        '000959.SZ', '000960.SZ', '000961.SZ', '000963.SZ', '000975.SZ',
        '000983.SZ', '000988.SZ', '000990.SZ', '000997.SZ', '000998.SZ',
        '002001.SZ', '002008.SZ', '002010.SZ', '002013.SZ', '002019.SZ',
        '002024.SZ', '002027.SZ', '002030.SZ', '002032.SZ', '002044.SZ',
        '002049.SZ', '002050.SZ', '002056.SZ', '002064.SZ', '002065.SZ',
        '002074.SZ', '002078.SZ', '002081.SZ', '002120.SZ', '002128.SZ',
        '002131.SZ', '002138.SZ', '002146.SZ', '002152.SZ', '002153.SZ',
        '002155.SZ', '002156.SZ', '002179.SZ', '002180.SZ', '002185.SZ',
        '002191.SZ', '002195.SZ', '002202.SZ', '002203.SZ', '002212.SZ',
        '002223.SZ', '002240.SZ', '002241.SZ', '002244.SZ', '002252.SZ',
        '002266.SZ', '002273.SZ', '002285.SZ', '002294.SZ', '002299.SZ',
        '002311.SZ', '002340.SZ', '002352.SZ', '002353.SZ', '002368.SZ',
    ]

    # ── 热门交易标的 ────────────────────────────────────────────
    POPULAR = [
        # 大蓝筹
        '600519.SH',  # 贵州茅台
        '000858.SZ',  # 五粮液
        '600036.SH',  # 招商银行
        '601318.SH',  # 中国平安
        '000333.SZ',  # 美的集团
        '000651.SZ',  # 格力电器
        '600887.SH',  # 伊利股份
        '002415.SZ',  # 海康威视
        '600276.SH',  # 恒瑞医药
        '300750.SZ',  # 宁德时代
        # 科技热门
        '002594.SZ',  # 比亚迪
        '688981.SH',  # 中芯国际
        '002230.SZ',  # 科大讯飞
        '300059.SZ',  # 东方财富
        '600703.SH',  # 三安光电
        '002475.SZ',  # 立讯精密
        '300124.SZ',  # 汇川技术
        '688041.SH',  # 海光信息
        # 金融龙头
        '601398.SH',  # 工商银行
        '601288.SH',  # 农业银行
        '600030.SH',  # 中信证券
        '601166.SH',  # 兴业银行
        # 消费
        '600690.SH',  # 海尔智家
        '000568.SZ',  # 泸州老窖
        '600809.SH',  # 山西汾酒
        '002304.SZ',  # 洋河股份
        # 能源/资源
        '601857.SH',  # 中国石油
        '600028.SH',  # 中国石化
        '601088.SH',  # 中国神华
        '600900.SH',  # 长江电力
    ]

    # ── 常用ETF ─────────────────────────────────────────────────
    ETF = [
        '510050.SH',  # 上证50ETF
        '510300.SH',  # 沪深300ETF华泰
        '510330.SH',  # 沪深300ETF华夏
        '510500.SH',  # 中证500ETF
        '512100.SH',  # 中证1000ETF
        '159915.SZ',  # 创业板ETF
        '159919.SZ',  # 沪深300ETF嘉实
        '512010.SH',  # 医药ETF
        '512480.SH',  # 半导体ETF
        '515030.SH',  # 新能源车ETF
        '512880.SH',  # 证券ETF
        '512690.SH',  # 白酒ETF
        '515790.SH',  # 光伏ETF
        '512800.SH',  # 银行ETF
        '159941.SZ',  # 纳指ETF
        '513100.SH',  # 纳指100ETF
        '518880.SH',  # 黄金ETF
        '511010.SH',  # 国债ETF
        '159605.SZ',  # 中概互联ETF
        '513050.SH',  # 中概互联网ETF
    ]

    # ── 宽基指数代理（用于 regime filter）───────────────────────
    INDEX_PROXY = {
        'hs300': '510300.SH',   # 沪深300ETF
        'zz500': '510500.SH',   # 中证500ETF
        'cyb':   '159915.SZ',   # 创业板ETF
        'sz50':  '510050.SH',   # 上证50ETF
    }

    # ── 全市场代码范围生成 ──────────────────────────────────────

    @classmethod
    def generate_full_market(cls) -> List[str]:
        """
        生成全市场A股代码列表

        覆盖:
        - 上海主板: 600000-601999, 603000-603999, 605000-605999
        - 上海科创板: 688000-689999
        - 深圳主板: 000001-000999
        - 深圳中小板: 002001-004999
        - 深圳创业板: 300001-301999
        - 北交所: 暂不覆盖 (8xxxxx, 4xxxxx)

        注: 不是所有代码都有上市股票，fetcher 会自动跳过无数据品种
        """
        codes = []

        # 上海主板
        for i in range(600000, 602000):
            codes.append(f'{i:06d}.SH')
        for i in range(603000, 604000):
            codes.append(f'{i:06d}.SH')
        for i in range(605000, 606000):
            codes.append(f'{i:06d}.SH')

        # 上海科创板
        for i in range(688000, 690000):
            codes.append(f'{i:06d}.SH')

        # 深圳主板
        for i in range(1, 1000):
            codes.append(f'{i:06d}.SZ')

        # 深圳中小板
        for i in range(2001, 5000):
            codes.append(f'{i:06d}.SZ')

        # 深圳创业板
        for i in range(300001, 302000):
            codes.append(f'{i:06d}.SZ')

        return codes

    # ── 已发现的有效品种管理 ────────────────────────────────────

    _VALID_SYMBOLS_FILE = "valid_symbols.csv"

    @classmethod
    def _valid_symbols_path(cls) -> Path:
        repo = Path(__file__).resolve().parents[2]
        return repo / "data" / "astock" / "csvconfig" / cls._VALID_SYMBOLS_FILE

    @classmethod
    def load_valid_symbols(cls) -> List[str]:
        """加载已验证的有效品种列表"""
        fpath = cls._valid_symbols_path()
        if not fpath.exists():
            return []
        try:
            df = pd.read_csv(fpath)
            return sorted(df["Instrument"].tolist())
        except Exception as e:
            logger.warning("Cannot load valid symbols: %s", e)
            return []

    @classmethod
    def save_valid_symbols(cls, symbols: List[str]):
        """保存有效品种列表"""
        fpath = cls._valid_symbols_path()
        fpath.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame({"Instrument": sorted(set(symbols))})
        df.to_csv(fpath, index=False)
        logger.info("Saved %d valid symbols to %s", len(df), fpath)

    @classmethod
    def update_valid_symbols(cls, new_symbols: List[str]):
        """增量更新有效品种列表"""
        existing = set(cls.load_valid_symbols())
        existing.update(new_symbols)
        cls.save_valid_symbols(sorted(existing))

    # ── 统一入口 ────────────────────────────────────────────────

    @classmethod
    def get(cls, name: str) -> List[str]:
        """
        获取股票池

        Args:
            name: 池名称
                - sse50, hs300, zz500, popular, etf
                - all       — 预定义池去重合集
                - full      — 全市场代码范围（~10000+，含空号）
                - valid     — 已发现的有效品种
                - test      — 3只测试用

        Returns:
            List of ts_code strings
        """
        pools = {
            'sse50':   cls.SSE50,
            'hs300':   cls.HS300_CORE,
            'zz500':   cls.ZZ500_CORE,
            'popular': cls.POPULAR,
            'etf':     cls.ETF,
            'all':     sorted(set(
                cls.SSE50 + cls.HS300_CORE + cls.ZZ500_CORE +
                cls.POPULAR + cls.ETF
            )),
            'test':    ['600519.SH', '000858.SZ', '600036.SH'],
        }

        name_lower = name.lower()

        if name_lower == 'full':
            return cls.generate_full_market()
        elif name_lower == 'valid':
            valid = cls.load_valid_symbols()
            if valid:
                return valid
            logger.warning("No valid symbols found, falling back to 'all' pool")
            return pools['all']
        elif name_lower in pools:
            return pools[name_lower]
        else:
            logger.warning("Unknown pool '%s', using 'popular'", name)
            return pools['popular']

    @classmethod
    def get_regime_proxy(cls, market: str = 'hs300') -> str:
        """获取 regime filter 代理标的"""
        return cls.INDEX_PROXY.get(market, '510300.SH')

    @classmethod
    def available_pools(cls) -> List[str]:
        """列出可用股票池"""
        return ['sse50', 'hs300', 'zz500', 'popular', 'etf', 'all', 'full', 'valid', 'test']

    @classmethod
    def pool_sizes(cls) -> Dict[str, int]:
        """获取各池大小"""
        return {name: len(cls.get(name)) for name in cls.available_pools()}

    @classmethod
    def get_sector(cls, sector: str) -> List[str]:
        """
        按板块获取

        Args:
            sector: sh_main, sh_star, sz_main, sz_sme, sz_gem
        """
        sectors = {
            'sh_main': [c for c in cls.generate_full_market()
                        if c.endswith('.SH') and not c.startswith('688')],
            'sh_star': [c for c in cls.generate_full_market()
                        if c.startswith('688')],
            'sz_main': [c for c in cls.generate_full_market()
                        if c.endswith('.SZ') and c[:3] == '000'],
            'sz_sme':  [c for c in cls.generate_full_market()
                        if c.endswith('.SZ') and c[:3] == '002'],
            'sz_gem':  [c for c in cls.generate_full_market()
                        if c.endswith('.SZ') and c[:3] in ('300', '301')],
        }
        return sectors.get(sector.lower(), [])


if __name__ == "__main__":
    print("A股股票池:")
    for pool in AStockUniverse.available_pools():
        symbols = AStockUniverse.get(pool)
        print(f"  {pool}: {len(symbols)} 只")
    print(f"\nRegime代理: {AStockUniverse.get_regime_proxy()}")
    print(f"\n板块:")
    for sector in ['sh_main', 'sh_star', 'sz_main', 'sz_sme', 'sz_gem']:
        print(f"  {sector}: {len(AStockUniverse.get_sector(sector))} codes")
