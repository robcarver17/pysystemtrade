from systems.provided.futures_chapter15.basesystem import futures_system
from systems.provided.moretradingrules.morerules import long_bias, short_bias
from copy import copy
import numpy as np
import pandas as pd

base_system=futures_system()

config = copy(base_system.config)

config.percentage_vol_target=16.0

## long lived vol estimate. comment out to use standard one
#config.volatility_calculation['days']=999999999
config.volatility_calculation['days']=35
config.trading_rules=dict(long_bias=long_bias, short_bias=short_bias)
config.instrument_weights=dict(US10=0.5, US5=0.5)
#config.instrument_weights=dict(US10=0.5, SP500=0.5)
#
#config.forecast_weights=dict(US10=dict(long_bias=1.0), SP500=dict(long_bias=1.0))
#config.forecast_weights=dict(US10=dict(long_bias=1.0), US5=dict(long_bias=1.0))
# or for relative value
config.forecast_weights=dict(US10=dict(long_bias=1.0), US5=dict(short_bias=1.0))

config.forecast_div_multiplier = 1.0

system=futures_system(config=config)
pandl=system.accounts.portfolio().percent()
pandl=pandl[pd.datetime(1990,1,1):]
#pandl=pandl[pd.datetime(1998,1,1):]
pandl[pandl==0]=np.nan
pandl[abs(pandl)>10.0]=np.nan

config.instrument_div_multiplier=config.instrument_div_multiplier/pandl.std()

system=futures_system(config=config)
pandl=system.accounts.portfolio().percent()
pandl[pandl==0]=np.nan
pandl[abs(pandl)>5.0]=np.nan
pandl=pandl[pd.datetime(1990,1,1):]
#pandl=pandl[pd.datetime(1998,1,1):]

import statsmodels.api as sm
import pylab


sm.qqplot(pandl.values, line='45')
pylab.show()

pandl.ffill().rolling(100).std().plot()

x=system.accounts.pandl_across_subsystems()
y=x.to_frame()
z=y.rolling(100).corr()
values = [-z.iloc[rowid,:][1] for rowid in range(int(len(z)/2))]
values = pd.DataFrame(list(values), x.index)