from systems.provided.futures_chapter15.basesystem import *
import pandas as pd
from matplotlib.pyplot import show, plot

system=futures_system()
system.set_logging_level("on")


trading_rules=system.rules.trading_rules()

del(system.config.instrument_weights) ## so we use all the markets we have, equal weighted

instrument_list=system.get_instrument_list()
system.config.instrument_weights=dict([(code, 1.0/len(instrument_list)) for code in instrument_list])

del(system.config.forecast_weights) ## not used anyway; so we have all trading rules

for rule_name in trading_rules:
    
    print(rule_name)
    print(system.accounts.pandl_for_trading_rule(rule_name).t_test())
    print(system.accounts.pandl_for_trading_rule(rule_name).sharpe())
    print(rule_name)
    print("***********************")
        
        