from systems.provided.futures_chapter15.estimatedsystem import futures_system
from sysdata.configdata import Config
my_config = Config("examples.breakout.breakoutfuturesestimateconfig.yaml")

system = futures_system(config=my_config)
system.config.notional_trading_capital = 100000
system.set_logging_level("on")
system.accounts.portfolio().stats()
system.portfolio.get_instrument_weights().plot()
from matplotlib.pyplot import show
show()
