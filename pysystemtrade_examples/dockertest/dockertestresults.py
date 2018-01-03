from systems.provided.futures_chapter15.basesystem import futures_system
from matplotlib.pyplot import show

resultsdir = "/home/rob/results"

system = futures_system(log_level="on")
system.unpickle_cache("", resultsdir + "/dockertest.pck")
# this will run much faster and reuse previous calculations
print(system.accounts.portfolio().sharpe())
