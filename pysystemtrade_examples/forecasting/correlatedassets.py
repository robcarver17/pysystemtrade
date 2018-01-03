from matplotlib.pyplot import plot, scatter
import numpy as np
from scipy.stats import linregress
import statsmodels.formula.api as sm

from systems.provided.futures_chapter15.basesystem import futures_system
import pandas as pd
from systems.forecasting import TradingRule
from systems.provided.moretradingrules.morerules import long_bias
from copy import copy

system=futures_system()
carry_acc=system.accounts.pandl_for_instrument_forecast("US10", "carry")
ewmac8_acc=system.accounts.pandl_for_instrument_forecast("US10", "ewmac8_32")
ewmac16_acc=system.accounts.pandl_for_instrument_forecast("US10", "ewmac16_64")

all_rets = pd.concat([carry_acc, ewmac8_acc, ewmac16_acc], axis=1)

# benchmarking
all_curve = system.accounts.pandl_for_instrument("MXP").percent()
all_curve=1.5*all_curve

new_rule = TradingRule(long_bias)
config = copy(system.config)
config.trading_rules['long_bias']=new_rule

## If you're using fixed weights and scalars

config.forecast_scalar=1.0
config.forecast_weights=dict(long_bias=1.0)  ## all existing forecast weights will need to be updated
config.forecast_div_multiplier=1.0
system2 = futures_system(config=config)

long_acc=system2.accounts.pandl_for_instrument_forecast("MXP", "long_bias")

both = pd.concat([long_acc, all_curve], axis=1)
both[pd.datetime(1982,9,15):pd.datetime(1982,9,21)]=np.nan

both.columns = ['Long_only', 'Strategy']


longonly_values=[]
strategyvalues=[]
for i in range(len(both.index)):
    long_value=both.Long_only[i]
    strategy_value = both.Strategy[i]
    if not(np.isnan(long_value) or np.isnan(strategy_value)):
        longonly_values.append(long_value)
        strategyvalues.append(strategy_value)

scatter(longonly_values, strategyvalues)

result = sm.ols(formula="Strategy ~ Long_only", data=both).fit()



ewmac8_acc=system.accounts.pandl_for_instrument_forecast("US10", "ewmac64_256")
ewmac16_acc=system.accounts.pandl_for_instrument_forecast("US10", "ewmac32_128")

both = pd.concat([ewmac8_acc, ewmac16_acc], axis=1)

both.columns = ['Existing', 'New']

existingvalues=[]
strategyvalues=[]
for i in range(len(both.index)):
    existing_value=both.Existing[i]
    strategy_value = both.New[i]
    if not(np.isnan(existing_value) or np.isnan(strategy_value)):
        existingvalues.append(existing_value)
        strategyvalues.append(strategy_value)

scatter(existingvalues, strategyvalues)

result = sm.ols(formula="New ~ Existing", data=both).fit()
