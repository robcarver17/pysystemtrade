from sysdata.config.production_config import get_production_config


def get_list_of_stale_instruments() -> list:
    config = get_production_config()
    stale_instruments = config.get_element_or_default("stale_instruments", [])

    return stale_instruments


def get_list_of_stale_strategies() -> list:
    config = get_production_config()
    return config.get_element_or_default("stale_strategies", [])
