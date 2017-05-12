from matplotlib.pyplot import show, title
from systems.provided.futures_chapter15.estimatedsystem import futures_system

system = futures_system()
system.config.forecast_weight_estimate["pool_instruments"] = True
system.config.forecast_weight_estimate["method"] = "bootstrap"
system.config.forecast_weight_estimate["equalise_means"] = False
system.config.forecast_weight_estimate["monte_runs"] = 200
system.config.forecast_weight_estimate["bootstrap_length"] = 104

system = futures_system(config=system.config)

system.combForecast.get_raw_forecast_weights("CORN").plot()
title("CORN")
show()
