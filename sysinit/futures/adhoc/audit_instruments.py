from sysdata.config.configdata import Config
from sysdata.config.instruments import get_duplicate_list_of_instruments_to_remove_from_config, \
    get_list_of_untradeable_instruments_in_config, get_list_of_bad_instruments_in_config
from sysdata.config.production_config import get_production_config
from sysproduction.data.prices import get_list_of_instruments
from systems.basesystem import get_instrument_weights_from_config

instruments_with_prices = get_list_of_instruments()
print(f"instruments_with_prices = {instruments_with_prices}")

prod_config = get_production_config()

duplicate_instruments = get_duplicate_list_of_instruments_to_remove_from_config(prod_config)
print(f"duplicate_instruments = {duplicate_instruments}")

untradeable_instruments = get_list_of_untradeable_instruments_in_config(prod_config)
print(f"untradeable_instruments = {untradeable_instruments}")

bad_instruments = get_list_of_bad_instruments_in_config(prod_config)
print(f"bad_instruments = {bad_instruments}")

instruments_to_remove = duplicate_instruments + untradeable_instruments + bad_instruments
print(f"instruments_to_remove = {instruments_to_remove}")

traded_instruments = set(instruments_with_prices) - set(instruments_to_remove)
print(f"traded_instruments = {traded_instruments}")

system_config = Config("/home/todd/private/system_config.yaml")
instrument_weights = get_instrument_weights_from_config(system_config)
system_instruments = list(instrument_weights.keys())
print(f"system_instruments = {system_instruments}")

missing_instruments = traded_instruments - set(system_instruments)
print(f"missing_instruments = {missing_instruments}")
