from matplotlib.pyplot import show, title

from systems.provided.futures_chapter15.estimatedsystem import futures_system

system=futures_system()
system.set_logging_level("on")
del(system.config.trading_rules) ## so we use all rules