import logging

from systems.provided.rob_system.run_system import futures_system

logging.getLogger("arctic").setLevel(logging.ERROR)

system = futures_system(config_filename="/home/todd/private/system_config.yaml")

system.log.msg("Sharpe Ratio: " + str(system.accounts.portfolio().sharpe()))

# Daily % gain/loss
# with pd.option_context('display.max_rows', None):
#    print(system.accounts.portfolio().percent())

# system.accounts.portfolio().curve().plot()

print(system.accounts.portfolio().stats())
