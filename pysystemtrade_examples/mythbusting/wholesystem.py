from systems.provided.futures_chapter15.basesystem import *
import pandas as pd
import numpy as np
from matplotlib.pyplot import show, plot, scatter, gca
from syscore.pdutils import align_to_joint, uniquets, divide_df_single_column
from syscore.dateutils import generate_fitting_dates
from syscore.algos import robust_vol_calc

from systems.portfolio import Portfolios
config = Config("systems.provided.futures_chapter15.futuresconfig.yaml")

# so we use all the markets we have, equal weighted
del (config.instrument_weights)
config.notional_trading_capital = 10000000
config.use_instrument_weight_estimates = True
config.use_forecast_weight_estimates = True

system = System([
    Account(), Portfolios(), PositionSizing(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules()
], csvFuturesData(), config)
system.set_logging_level("on")

# avgs
instrument_list = system.get_instrument_list()
trading_rules = system.rules.trading_rules().keys()

ans = dict()
for instrument_code in instrument_list:
    ans[instrument_code] = dict()
    for rule in trading_rules:
        ans[instrument_code][
            rule] = system.accounts.pandl_for_instrument_forecast(
                instrument_code, rule).sharpe()

# average rule / instrument
ans = []
for instrument_code in instrument_list:
    for rule in trading_rules:
        ans.append(
            system.accounts.pandl_for_instrument_forecast(
                instrument_code, rule).sharpe())

np.mean(ans)

# average Rule
ans = []
for rule in trading_rules:
    ans.append(system.accounts.pandl_for_trading_rule(rule).sharpe())

print(ans)

# average instrument
ans = []
for instrument_code in instrument_list:
    ans.append(system.accounts.pandl_for_subsystem(instrument_code).sharpe())

print(ans)

# portfolio
system.accounts.portfolio().sharpe()
