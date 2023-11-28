from systems.provided.example.simplesystem import simplesystem

my_system = simplesystem()
print(my_system)
print(my_system.portfolio.get_notional_position("SOFR").tail(5))

from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysdata.config.configdata import Config

"""
Now loading config and data
"""

my_config = Config("systems.provided.example.simplesystemconfig.yaml")
my_data = csvFuturesSimData()
my_system = simplesystem(config=my_config, data=my_data)
print(my_system.portfolio.get_notional_position("SOFR").tail(5))
"""
Let's get the chapter 15 system
"""

from systems.provided.futures_chapter15.basesystem import futures_system
from matplotlib.pyplot import show

system = futures_system()
print(system.accounts.portfolio().sharpe())
system.accounts.portfolio().curve().plot()
show()
"""
Same for estimated system
"""

from systems.provided.futures_chapter15.estimatedsystem import futures_system

system = futures_system()
print(system.accounts.portfolio().sharpe())
system.accounts.portfolio().curve().plot()
system.cache.pickle("private.this_system_name.pck")
show()

del system  # just to make sure
system = futures_system()
system.cache.unpickle("private.this_system_name.pck")
# this will run much faster and reuse previous calculations
system.accounts.portfolio().sharpe()
