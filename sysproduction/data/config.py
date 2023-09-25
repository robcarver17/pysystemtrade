from sysdata.config.production_config import get_production_config
from sysobjects.production.tradeable_object import listOfInstrumentStrategies

###### stale


def remove_stale_instruments_and_strategies_from_list_of_instrument_strategies(
    list_of_instrument_strategies: listOfInstrumentStrategies,
) -> listOfInstrumentStrategies:
    filtered_list = remove_stale_instruments_from_list_of_instrument_strategies(
        list_of_instrument_strategies
    )
    twice_filtered_list = remove_stale_strategies_from_list_of_instrument_strategies(
        filtered_list
    )

    return twice_filtered_list


def remove_stale_instruments_from_list_of_instrument_strategies(
    list_of_instrument_strategies: listOfInstrumentStrategies,
) -> listOfInstrumentStrategies:
    list_of_stale_instruments = get_list_of_stale_instruments()
    filtered_list = list_of_instrument_strategies.filter_to_remove_list_of_instruments(
        list_of_stale_instruments
    )
    return filtered_list


def remove_stale_instruments_from_list_of_instruments(
    list_of_instrument_codes: list,
) -> list:
    list_of_stale_instruments = get_list_of_stale_instruments()
    filtered_list = [
        instrument_code
        for instrument_code in list_of_instrument_codes
        if instrument_code not in list_of_stale_instruments
    ]
    return filtered_list


def remove_stale_strategies_from_list_of_instrument_strategies(
    list_of_instrument_strategies: listOfInstrumentStrategies,
) -> listOfInstrumentStrategies:
    list_of_stale_strategies = get_list_of_stale_strategies()
    filtered_list = list_of_instrument_strategies.filter_to_remove_list_of_strategies(
        list_of_stale_strategies
    )
    return filtered_list


def get_list_of_stale_instruments() -> list:
    config = get_production_config()
    return get_list_of_stale_instruments_given_config(config)


def get_list_of_stale_instruments_given_config(config) -> list:
    stale_instruments = config.get_element_or_default("stale_instruments", [])

    return stale_instruments


def get_list_of_stale_strategies() -> list:
    config = get_production_config()
    return config.get_element_or_default("stale_strategies", [])
