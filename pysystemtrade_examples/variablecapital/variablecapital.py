from matplotlib.pyplot import show
from systems.provided.futures_chapter15.basesystem import futures_system

system = futures_system(log_level="on")
system.config.instrument_weights = dict(EDOLLAR=1.0)

system.config.capital_multiplier['func'] = 'syscore.capital.fixed_capital'
"""
system.accounts.portfolio().curve().plot()
show()



system.accounts.portfolio().percent().curve().plot()
show()

system.accounts.portfolio().cumulative().curve().plot()
show()
"""
pandl_fixed = system.accounts.portfolio()

print(system.accounts.portfolio().capital)
"""
system = futures_system(log_level="on")
system.config.instrument_weights=dict(EDOLLAR=1.0)
system.config.capital_multiplier['func']='syscore.capital.full_compounding'

system.accounts.capital_multiplier().plot()
show()

system.accounts.portfolio_with_multiplier().capital.plot()
show()

system.accounts.portfolio_with_multiplier().curve().plot()
show()



system.accounts.get_buffered_position_with_multiplier("EDOLLAR", False).plot()
system.accounts.get_buffered_position("EDOLLAR", False).plot()
show()


"""

system = futures_system(log_level="on")
system.config.instrument_weights = dict(EDOLLAR=1.0)
system.config.capital_multiplier['func'] = 'syscore.capital.half_compounding'
"""
system.accounts.capital_multiplier().plot()
show()

system.accounts.portfolio_with_multiplier().capital.plot()
show()

system.accounts.portfolio_with_multiplier().curve().plot()
show()



system.accounts.get_buffered_position_with_multiplier("EDOLLAR", False).plot()
system.accounts.get_buffered_position("EDOLLAR", False).plot()
show()
"""

pandl_variable = system.accounts.portfolio_with_multiplier()
pandl_fixed.curve().plot()
pandl_variable.curve().plot()
show()
