from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import create_variations, TradingRule

dict_of_speeds= [dict(Lfast=4, Lslow=16), dict(Lfast=8, Lslow=32),
                                           dict(Lfast=16, Lslow=64),
                                           dict(Lfast=32, Lslow=128), dict(Lfast=64, Lslow=256)]

normmom_base_rule= TradingRule('systems.provided.futures_chapter15.rules.ewmac', data=['rawdata.cumulative_norm_return',
                                                                                       'rawdata.daily_returns_volatility'])
normmom_variations = create_variations(normmom_base_rule, dict_of_speeds,
                               key_argname='Lfast', nameformat="normmom_%s:%s")

aggmom_base_rule = TradingRule('systems.provided.futures_chapter15.rules.ewmac', data=['rawdata.normalised_price_for_asset_class',
                                                                                       'rawdata.daily_returns_volatility'])
aggmom_variations = create_variations(aggmom_base_rule, dict_of_speeds,
                               key_argname='Lfast', nameformat="aggmom_%s:%s")

standardmom_base_rule = TradingRule('systems.provided.futures_chapter15.rules.ewmac', data= ['rawdata.get_daily_prices', 'rawdata.daily_returns_volatility'])
standardmom_variations = create_variations(standardmom_base_rule, dict_of_speeds,
                               key_argname='Lfast', nameformat="standardmom_%s:%s")


# I f***** love python 3
variations = {**normmom_variations, **aggmom_variations, **standardmom_variations}

sys=futures_system(trading_rules=variations)

# equal weighting across instruments
del(sys.config.instrument_weights)

# but estimated IDM
sys.config.use_instrument_div_mult_estimates=True

# going to estimate forecast weights

sys.config.use_forecast_scale_estimates=True
sys.config.use_forecast_weight_estimates=True
sys.config.use_forecast_div_mult_estimates=True

del(sys.config.forecast_weights)

allpandl=sys.accounts.pandl_for_all_trading_rules().to_frame()
standardpandl=allpandl[list(standardmom_variations.keys())]
aggmompandl=allpandl[list(aggmom_variations.keys())]*2.08
normmomepandl=allpandl[list(normmom_variations.keys())]*2.17

import pandas as pd
thing=pd.concat([standardpandl.sum(axis=1).cumsum(), normmomepandl.sum(axis=1).cumsum()],axis=1)
thing.columns=['Standard',  'Normalised']
thing.plot()

thing=pd.concat([standardpandl.sum(axis=1).cumsum(),aggmompandl.sum(axis=1).cumsum(), normmomepandl.sum(axis=1).cumsum()],axis=1)
thing.columns=['Standard', 'Aggregate', 'Normalised']