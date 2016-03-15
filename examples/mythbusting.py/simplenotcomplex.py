from systems.provided.futures_chapter15.basesystem import *
import pandas as pd
from matplotlib.pyplot import show, plot

system=futures_system()


system=futures_system(trading_rules=dict(draw20=draw_a_line))
system.config.use_forecast_scale_estimates=True
system.config.forecast_weights=dict(draw20=1.0)
del(system.config.instrument_weights) ## so we use all the markets we have
del(system.config.forecast_weights) ## so we use all the trading rules we have
system.rules.get_raw_forecast("BTP", "draw20").plot()
show()

system.accounts.forecast_turnover("BTP", "draw20")
