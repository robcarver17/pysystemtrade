import matplotlib

matplotlib.use("TkAgg")
from systems.provided.futures_chapter15.basesystem import futures_system

sys = futures_system()
sys.config.forecast_floor = 0
sys.forecastScaleCap.get_capped_forecast("SP500", "ewmac2_8").plot()

from systems.forecasting import create_variations, TradingRule

dict_of_speeds = [
    dict(Lfast=4, Lslow=16),
    dict(Lfast=8, Lslow=32),
    dict(Lfast=16, Lslow=64),
    dict(Lfast=32, Lslow=128),
    dict(Lfast=64, Lslow=256),
]

normmom_base_rule = TradingRule(
    "systems.provided.futures_chapter15.rules.ewmac_calc_vol",
    data=["rawdata.cumulative_norm_return"],
)
normmom_variations = create_variations(
    normmom_base_rule,
    dict_of_speeds,
    key_argname="Lfast",
    nameformat="normmom_%s:%s")

TradingRule(
    rule="systems.provided.futures_chapter15.rules.ewmac_calc_vol",
    data=["rawdata.cumulative_norm_return"],
    other_args=dict(Lfast=4, Lslow=16),
)

aggmom_base_rule = TradingRule(
    "systems.provided.futures_chapter15.rules.ewmac_calc_vol",
    data=["rawdata.normalised_price_for_asset_class"],
)
aggmom_variations = create_variations(
    aggmom_base_rule,
    dict_of_speeds,
    key_argname="Lfast",
    nameformat="aggmom_%s:%s")

standardmom_base_rule = TradingRule(
    "systems.provided.futures_chapter15.rules.ewmac",
    data=["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
)
standardmom_variations = create_variations(
    standardmom_base_rule,
    dict_of_speeds,
    key_argname="Lfast",
    nameformat="standardmom_%s:%s",
)

# I f***** love python 3
variations = {**normmom_variations, **aggmom_variations, **standardmom_variations}

sys = futures_system(trading_rules=variations)

# equal weighting across instruments
del sys.config.instrument_weights

# but estimated IDM
sys.config.use_instrument_div_mult_estimates = True
