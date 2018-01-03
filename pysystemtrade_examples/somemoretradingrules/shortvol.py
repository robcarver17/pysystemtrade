from systems.provided.futures_chapter15.basesystem import *

sys=futures_system()
sys.config.instrument_weights = dict(VIX=0.5, V2X = 0.5)
sys.config.trading_rules=dict(shortbias=dict(function='systems.provided.moretradingrules.morerules.short_bias'))
sys.config.use_forecast_scale_estimates=True
del(sys.config.forecast_weights)

ans=sys.accounts.portfolio()

ans.plot()

ans.monthly.stats()

# measure skew on equities
sys.cache.clear()
sys.config.instrument_weights = dict(SP500 = 1.0)
sys.accounts.portfolio().monthly.stats()

# what about if we throw carry and trend following back into the mix?
sys=futures_system()
sys.config.instrument_weights = dict(VIX=0.5, V2X = 0.5)
sys.config.use_forecast_scale_estimates=True
sys.config.use_forecast_div_mult_estimates=True
sys.config.use_forecast_weight_estimates = True
ans2 = sys.accounts.portfolio()

# now with short bias
sys=futures_system()
sys.config.instrument_weights = dict(VIX=0.5, V2X = 0.5)
sys.config.use_forecast_scale_estimates=True
sys.config.use_forecast_div_mult_estimates=True
sys.config.use_forecast_weight_estimates = True
sys.config.trading_rules['shortbias']=dict(function='systems.provided.moretradingrules.morerules.short_bias')
ans3 = sys.accounts.portfolio()


