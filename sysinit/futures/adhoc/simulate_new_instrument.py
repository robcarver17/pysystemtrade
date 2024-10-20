import matplotlib
from matplotlib import pyplot as plt

from systems.provided.futures_chapter15.basesystem import *

instrument = "LUMBER"

system = futures_system()
system.config.instrument_weights = {instrument: 1.0}

print(system.data.get_raw_price(instrument))
print(system.data.get_instrument_raw_carry_data(instrument))
print(system.data.get_raw_cost_data(instrument))

system.rules.get_raw_forecast(instrument, "ewmac64_256").plot()
matplotlib.use('TkAgg')
plt.show()

system.rules.get_raw_forecast(instrument, "carry").plot()
plt.show()

system.combForecast.get_combined_forecast(instrument).plot()
plt.show()

system.positionSize.get_subsystem_position(instrument).plot()
plt.show()

print(system.positionSize.get_volatility_scalar(instrument))

print(system.accounts.get_SR_cost_per_trade_for_instrument(instrument))

system.accounts.pandl_for_instrument(instrument).curve().plot()
plt.show()
