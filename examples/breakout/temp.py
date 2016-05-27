from systems.provided.futures_chapter15.basesystem import futures_system
from matplotlib.pyplot import show

system = futures_system(log_level="on")
print(system.accounts.portfolio().sharpe())
system.accounts.portfolio().curve().plot()
show()

system.accounts.portfolio().as_cumulative().plot()
show()

system.accounts.portfolio().as_cum_percent().plot()
show()

system.accounts.portfolio().as_percent().cumsum().plot()
show()
