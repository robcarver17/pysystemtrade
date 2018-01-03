from matplotlib.pyplot import show, title

from systems.provided.futures_chapter15.estimatedsystem import futures_system

system = futures_system()
system.set_logging_level("on")
"""
system.forecastScaleCap.get_scaled_forecast("EDOLLAR", "carry").plot()
system.forecastScaleCap.get_scaled_forecast("V2X", "ewmac64_256").plot()
system.forecastScaleCap.get_scaled_forecast("CORN", "ewmac64_256").plot()

show()


system.combForecast.pandl_for_instrument_rules("US10").cumsum().plot()
show()


system.config.forecast_weight_estimate["pool_instruments"]=False
system.config.forecast_weight_estimate["method"]="bootstrap" ## speed things up
system.config.forecast_weight_estimate["equalise_means"]=False
system.config.forecast_weight_estimate["monte_runs"]=200
system.config.forecast_weight_estimate["bootstrap_length"]=104




system=futures_system(config=system.config)

system.combForecast.get_forecast_weights("CORN").plot()
title("CORN")
show()

system.combForecast.get_forecast_weights("EDOLLAR").plot()
title("EDOLLAR")
show()
"""

# reset the config
system = futures_system()
system.config.forecast_weight_estimate["pool_instruments"] = True
system.config.forecast_weight_estimate["method"] = "bootstrap"
system.config.forecast_weight_estimate["equalise_means"] = False
system.config.forecast_weight_estimate["monte_runs"] = 200
system.config.forecast_weight_estimate["bootstrap_length"] = 104
"""
system=futures_system(config=system.config)

system.combForecast.get_raw_forecast_weights("CORN").plot()
title("CORN")
show()

## check same weights
system.combForecast.get_raw_forecast_weights("US10").plot()
title("US10")
show()

system.combForecast.get_forecast_weights("CORN").plot()
title("CORN")
show()



system.combForecast.get_forecast_diversification_multiplier("EDOLLAR").plot()
show()

system.combForecast.get_forecast_diversification_multiplier("V2X").plot()
show()

system.combForecast.get_combined_forecast("EUROSTX").plot()
show()


system.positionSize.get_price_volatility("EUROSTX").plot()
show()

system.positionSize.get_block_value("EUROSTX").plot()
show()

system.positionSize.get_instrument_currency_vol("EUROSTX").plot()
show()

system.positionSize.get_instrument_value_vol("EUROSTX").plot()
show()

system.positionSize.get_volatility_scalar("EUROSTX").plot()
show()

system.positionSize.get_subsystem_position("EUROSTX").plot()
show()

instrument_codes=system.get_instrument_list()

import pandas as pd

pandl_subsystems=[system.accounts.pandl_for_subsystem(code, percentage=True)
        for code in instrument_codes]

pandl=pd.concat(pandl_subsystems, axis=1)
pandl.columns=instrument_codes

pandl=pandl.cumsum().plot()
show()

"""

system.config.instrument_weight_estimate[
    "method"] = "bootstrap"  # speed things up
system.config.instrument_weight_estimate["equalise_means"] = False
system.config.instrument_weight_estimate["monte_runs"] = 200
system.config.instrument_weight_estimate["bootstrap_length"] = 104

system.portfolio.get_instrument_weights().plot()
show()

system.portfolio.get_instrument_diversification_multiplier().plot()
show()

print(system.portfolio.get_instrument_correlation_matrix().corr_list[16])
print(system.portfolio.get_instrument_correlation_matrix().corr_list[25])

system.portfolio.get_notional_position("EUROSTX").plot()
show()

print(system.accounts.portfolio().stats())

system.accounts.portfolio().cumsum().plot()

show()
