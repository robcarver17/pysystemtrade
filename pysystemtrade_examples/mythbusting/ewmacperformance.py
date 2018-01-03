from systems.provided.futures_chapter15.basesystem import *
import pandas as pd
from matplotlib.pyplot import show, plot

system = futures_system()
system.set_logging_level("on")

trading_rules = system.rules.trading_rules()

# so we use all the markets we have, equal weighted
del (system.config.instrument_weights)

instrument_list = system.get_instrument_list()
system.config.instrument_weights = dict([(code, 1.0 / len(instrument_list))
                                         for code in instrument_list])

# not used anyway; so we have all trading rules
del (system.config.forecast_weights)

# trading_rules=system.combForecast.get_trading_rule_list("US10")

for rule_name in trading_rules:

    print(rule_name)
    # system.accounts.pandl_for_trading_rule(rule_name).to_ncg_frame().cumsum().plot()
    # show()

    print(system.accounts.pandl_for_trading_rule(rule_name).t_test())
    print(system.accounts.pandl_for_trading_rule(rule_name).sharpe())
    print(rule_name)

    print("***********************")

for rule_name in ["ewmac16_64", "carry"]:
    print(rule_name)
    print("*****************")
    for instr_code in instrument_list:
        data = system.accounts.pandl_for_instrument_forecast(
            instr_code, rule_name)
        print("%s %.4f %.3f" % (instr_code, data.t_test()[1], data.sharpe()))

bigresults = []
for rule_name in trading_rules:
    results = []
    for instr_code in instrument_list:
        data = system.accounts.pandl_for_instrument_forecast(
            instr_code, rule_name)
        results.append(data.sharpe())

    results.sort()
    print(rule_name)
    print(results)
    bigresults = bigresults + results
