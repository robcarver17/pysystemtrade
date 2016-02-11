from matplotlib.pyplot import *
show()


from systems.provided.futures_chapter15.basesystem import *
from private.PU import *
system=futures_system(config=Config("private.PU.config.yaml"))

"""
instrument_code="US5"

system.combForecast.get_combined_forecast(instrument_code).plot()
show()


"""

ans=system.accounts.portfolio()
ans.cumsum().plot()
show()

print(ans.stats())

"""
for code in system.get_instrument_list():
    ans=system.portfolio.get_notional_position(code)
    ans.plot()
    title(code)

    show()
    
ans=system.accounts.portfolio()

ans.cumsum().plot()
print(ans.stats())

ans=[system.accounts.pandl_for_subsystem(code) for code in system.get_instrument_list()]
import pandas as pd
ans=pd.concat(ans, axis=1)
ans.columns=system.get_instrument_list()
ans.cumsum().plot()
show()

"""