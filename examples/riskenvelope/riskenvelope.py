from systems.provided.futures_chapter15.basesystem import futures_system
from matplotlib.pyplot import show, hist
import numpy as np

system = futures_system(log_level="on")

system.config.capital_multiplier['func'] = 'syscore.capital.half_compounding'

system.accounts.portfolio().percent().cumsum().plot()
show()

drawdowns = system.accounts.portfolio().percent().drawdown()
drawdowns.plot()
show()

drawdowns = system.accounts.portfolio_with_multiplier().percent().plot()
show()

drawdowns = system.accounts.portfolio_with_multiplier().percent().drawdown()
drawdowns.plot()
show()

distr_drawdowns = list(drawdowns.values)
distr_drawdowns = [x for x in distr_drawdowns if not np.isnan(x)]

hist(distr_drawdowns)
show()
