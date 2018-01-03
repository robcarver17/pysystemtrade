"""
Let's get the chapter 15 system
"""

from systems.provided.futures_chapter15.basesystem import futures_system
from matplotlib.pyplot import show

resultsdir = "/results"
system = futures_system(log_level="on")
print(system.accounts.portfolio().sharpe())
system.pickle_cache("", resultsdir + "/dockertest.pck")
