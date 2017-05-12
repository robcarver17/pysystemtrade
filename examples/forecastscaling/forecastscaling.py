from copy import copy
from matplotlib.pyplot import show, bar
from systems.provided.futures_chapter15.estimatedsystem import futures_system
"""
  cross sectional
"""

system = futures_system()

# don't pool
system.config.forecast_scalar_estimate['pool_instruments'] = False

instrument_list = system.get_instrument_list()
print(instrument_list)

results = []
for instrument_code in instrument_list:
    results.append(
        round(
            float(
                system.forecastScaleCap.get_forecast_scalar(
                    instrument_code, "ewmac2_8").tail(1).values), 2))
print(results)

results = []
for instrument_code in instrument_list:
    results.append(
        round(
            float(
                system.forecastScaleCap.get_forecast_scalar(
                    instrument_code, "carry").tail(1).values), 2))
print(results)
"""
 Use an expanding window
"""

system = futures_system()

# Let's use a one year rolling window instead
system.config.forecast_scalar_estimate['window'] = 250
system.config.forecast_scalar_estimate['min_periods'] = 250

system.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac64_256").plot()
show()
"""
 Goldilocks amount of minimum data - not too much, not too little
"""

system = futures_system()

# stupidly small number of min periods
system.config.forecast_scalar_estimate['min_periods'] = 50

# don't pool
system.config.forecast_scalar_estimate['pool_instruments'] = False

system.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac64_256").plot()
show()

system.rules.get_raw_forecast("EDOLLAR", "ewmac64_256").plot()
show()
"""

"""
