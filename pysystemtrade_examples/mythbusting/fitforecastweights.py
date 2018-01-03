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
config.forecast_weight_estimate = dict(
    pool_instruments=False, method="one_period")

system = System([
    Account(), Portfolios(), PositionSizing(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules()
], csvFuturesData(), config)
system.set_logging_level("on")
a1 = system.accounts.portfolio()

config = Config("systems.provided.futures_chapter15.futuresconfig.yaml")

# so we use all the markets we have, equal weighted
del (config.instrument_weights)
config.notional_trading_capital = 10000000
config.use_instrument_weight_estimates = True
config.use_forecast_weight_estimates = True
config.forecast_weight_estimate = dict(
    pool_instruments=True, method="one_period")

system = System([
    Account(), Portfolios(), PositionSizing(), FuturesRawData(),
    ForecastCombine(), ForecastScaleCap(), Rules()
], csvFuturesData(), config)
system.set_logging_level("on")
a2 = system.accounts.portfolio()

from syscore.accounting import account_test

print("Fit by instrument out of sample:")
print(a1.stats())
print("")
print("Fit across instruments out of sample")
print(a2.stats())

print("Test ")
print(account_test(a1, a2))

a3 = pd.concat([a1.curve(), a2.curve()], axis=1)
a3.columns = ["byinstr", "pooled"]
a3.plot()
show()
