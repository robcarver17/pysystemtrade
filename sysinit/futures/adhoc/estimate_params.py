import logging

from systems.diagoutput import systemDiag
from systems.provided.rob_system.run_system import futures_system

logging.getLogger("arctic").setLevel(logging.ERROR)

system = futures_system(config_filename="/home/todd/private/system_config.yaml")

system.config.use_forecast_scale_estimates = False
system.config.use_forecast_weight_estimates = False
system.config.use_forecast_div_mult_estimates = True
system.config.use_instrument_weight_estimates = False
system.config.use_instrument_div_mult_estimates = False

sysdiag = systemDiag(system)

# For single-instrument optimization
# system.config.instrument_weights = dict(BITCOIN=1.0)

sysdiag.yaml_config_with_estimated_parameters('someyamlfile.yaml',
                                              attr_names=['forecast_scalars',
                                                          'forecast_weights',
                                                          'forecast_div_multiplier',
                                                          'forecast_mapping',
                                                          'instrument_weights',
                                                          'instrument_div_multiplier'])

system.log.info("Sharpe Ratio: " + str(system.accounts.portfolio().sharpe()))
