from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import create_variations, TradingRule
from copy import copy


sys = futures_system()
del(sys.config.instrument_weights)

save_absolute_carry_rule = sys.config.trading_rules['carry']

# Trading rules
short_vol=dict(shortbias=dict(function='systems.provided.moretradingrules.morerules.short_bias'))

mean_reversion=dict(mr=dict(function='systems.provided.moretradingrules.morerules.cross_sectional_mean_reversion',
                                                 data=['rawdata.cumulative_norm_return',
                                                       'rawdata.normalised_price_for_asset_class'],other_args=dict(horizon=250)))

relative_carry_rule = dict(relativecarry=dict(function='systems.provided.moretradingrules.morerules.relative_carry',
                                                 data=['rawdata.smoothed_carry','rawdata.median_carry_for_asset_class']))

absolute_carry_rule =dict(carry=save_absolute_carry_rule)

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

new_trading_rules = {**normmom_variations, **aggmom_variations, **standardmom_variations,  **short_vol, **mean_reversion,
                     **relative_carry_rule, **absolute_carry_rule}

original_trading_rules = {**standardmom_variations, **absolute_carry_rule}

trading_rule_names=list(new_trading_rules.keys())
trading_rule_names_without_shortbias= copy(trading_rule_names)
trading_rule_names_without_shortbias.remove("shortbias")

sys_old=futures_system(trading_rules=original_trading_rules)
sys_new=futures_system(trading_rules=new_trading_rules)

# equal weighting across instruments
del(sys_new.config.instrument_weights)
del(sys_old.config.instrument_weights)

sys_new.config.rule_variations=dict([(instrument_code, trading_rule_names_without_shortbias) for instrument_code in sys_new.get_instrument_list()])
sys_new.config.rule_variations["VIX"]=trading_rule_names
sys_new.config.rule_variations["V2X"]=trading_rule_names


# but use estimated IDM
sys_new.config.use_instrument_div_mult_estimates=True
sys_old.config.use_instrument_div_mult_estimates=True

# going to estimate forecast weights

sys_old.config.use_forecast_scale_estimates=True
sys_old.config.use_forecast_weight_estimates=True
sys_old.config.use_forecast_div_mult_estimates=True
del(sys_old.config.forecast_weights)

sys_new.config.use_forecast_scale_estimates=True
sys_new.config.use_forecast_weight_estimates=True
sys_new.config.use_forecast_div_mult_estimates=True
del(sys_new.config.forecast_weights)

sys_old.accounts.portfolio().cumsum().plot()
sys_new.accounts.portfolio().cumsum().plot()

sys_old.cache.pickle("examples.somemoretradingrules.oldsystem.pck")
sys_old.cache.pickle("examples.somemoretradingrules.newsystem.pck")



sys_old.cache.unpickle("examples.somemoretradingrules.oldsystem.pck")
sys_new.cache.unpickle("examples.somemoretradingrules.newsystem.pck")