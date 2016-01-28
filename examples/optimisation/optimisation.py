from matplotlib.pyplot import show

from systems.provided.futures_chapter15.estimatedsystem import futures_system

system=futures_system()

system.set_logging_level("on")

system.config.forecast_weight_estimate["method"]="shrinkage" ## speed things up
system.config.instrument_weight_estimate["method"]="shrinkage" ## speed things up 

print(system.accounts.portfolio().stats())

system.accounts.portfolio().cumsum().plot()

show()