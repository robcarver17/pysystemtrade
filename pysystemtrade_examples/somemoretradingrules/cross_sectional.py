from systems.provided.futures_chapter15.basesystem import futures_system

sys=futures_system()

# equal weighting across instruments
del(sys.config.instrument_weights)

# but use estimated IDM
sys.config.use_instrument_div_mult_estimates=True

sys.config.trading_rules=dict(mr=dict(function='systems.provided.moretradingrules.morerules.cross_sectional_mean_reversion',
                                                 data=['rawdata.cumulative_norm_return',
                                                       'rawdata.normalised_price_for_asset_class'],other_args=dict(horizon=125)))

# going to estimate forecast weights

sys.config.use_forecast_scale_estimates=True
sys.config.use_forecast_weight_estimates=True
sys.config.use_forecast_div_mult_estimates=True

del(sys.config.forecast_weights)

mkt="US10"
sys.rawdata.cumulative_norm_return(mkt).plot()
sys.rawdata.normalised_price_for_asset_class(mkt).plot()

x=sys.rawdata.cumulative_norm_return(mkt)- sys.rawdata.normalised_price_for_asset_class(mkt)
x.plot()

sys.rules.get_raw_forecast(mkt, "mr").plot()

sys.accounts.pandl_for_instrument_forecast(mkt, "mr").cumsum().plot()

sys.accounts.portfolio().cumsum().plot()
