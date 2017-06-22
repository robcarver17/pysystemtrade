from systems.provided.futures_chapter15.basesystem import futures_system

sys=futures_system()

save_absolute_carry_rule = sys.config.trading_rules['carry']

# equal weighting across instruments
del(sys.config.instrument_weights)

# but estimated IDM
sys.config.use_instrument_div_mult_estimates=True

sys.config.trading_rules=dict(carry=save_absolute_carry_rule, relativecarry=dict(function='systems.provided.moretradingrules.morerules.relative_carry',
                                                 data=['rawdata.smoothed_carry','rawdata.median_carry_for_asset_class']))

# going to estimate forecast weights

sys.config.use_forecast_scale_estimates=True
sys.config.use_forecast_weight_estimates=True
sys.config.use_forecast_div_mult_estimates=True

del(sys.config.forecast_weights)

ans = sys.accounts.pandl_for_all_trading_rules()
ans2 = sys.accounts.pandl_for_all_trading_rules_unweighted()

ans2.to_frame().cumsum().plot()
ans2.get_stats("sharpe",freq="monthly")

ans.monthly.stats()
