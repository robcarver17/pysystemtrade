from matplotlib.pyplot import show, title
from systems.provided.futures_chapter15.estimatedsystem import futures_system
system = futures_system(log_level="on")
system.config.capital_multiplier['func']='syscore.capital.full_compounding'

system.accounts.capital_multiplier().plot()
show()

system.accounts.get_actual_capital().plot()
show()


system.accounts.portfolio_with_multiplier().percent().curve().plot()
show()

system.accounts.portfolio().percent().curve().plot()
show()
