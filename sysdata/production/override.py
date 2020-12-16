"""
An override is something that affects our normal trading behaviour
"""

from syslogdiag.log import logtoscreen
from sysobjects.production.override import Override
from sysobjects.production.strategy import instrumentStrategy
from sysdata.base_data import baseData

DEFAULT_OVERRIDE = Override(1.0)

strategy_overrides = "strategies"
instrument_overrides = "instruments"
strategy_instruments_overrides = "strategies_instruments"


class overrideData(baseData):
    def __init__(self, log=logtoscreen("Overrides")):
        super().__init__(log=log)

    def default_override(self):
        return DEFAULT_OVERRIDE

    def get_cumulative_override_for_instrument_strategy(self, instrument_strategy: instrumentStrategy) -> Override:
        strategy_override = self._get_override_for_strategy(instrument_strategy.strategy_name)
        instrument_override = self._get_override_for_instrument(instrument_strategy.instrument_code)
        strategy_instrument_override = self._get_override_for_instrument_strategy(
            instrument_strategy)

        return strategy_override * instrument_override * strategy_instrument_override

    def _get_override_for_strategy(self, strategy_name: str) -> Override:
        return self._get_override_object_for_type_and_key(strategy_overrides, strategy_name)

    def _get_override_for_instrument_strategy(
            self, instrument_strategy: instrumentStrategy) -> Override:
        key = _key_from_instrument_strategy(instrument_strategy)
        return self._get_override_object_for_type_and_key(
            strategy_instruments_overrides, key)

    def _get_override_for_instrument(self, instrument_code: str) -> Override:
        return self._get_override_object_for_type_and_key(
            instrument_overrides, instrument_code)

    def update_override_for_strategy(self, strategy_name: str, new_override: Override):
        self._update_override(strategy_overrides, strategy_name, new_override)

    def update_override_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy, new_override: Override
    ):
        key = _key_from_instrument_strategy(instrument_strategy)
        self._update_override(strategy_instruments_overrides, key, new_override)

    def update_override_for_instrument(self, instrument_code:str, new_override:Override):
        self._update_override(instrument_overrides, instrument_code, new_override)

    def get_dict_of_all_overrides(self) -> dict:
        strategy_dict = self._get_dict_of_strategies_with_overrides()
        strategy_instrument_dict = self._get_dict_of_strategy_instrument_with_overrides()
        instrument_dict = self._get_dict_of_instruments_with_overrides()

        all_overrides = {**strategy_dict, **strategy_instrument_dict, **instrument_dict}

        return all_overrides

    def _get_dict_of_strategies_with_overrides(self) ->dict:
        return self._get_dict_of_items_with_overrides_for_type(strategy_overrides)

    def _get_dict_of_strategy_instrument_with_overrides(self) ->dict:
        return self._get_dict_of_items_with_overrides_for_type(
            strategy_instruments_overrides)

    def _get_dict_of_instruments_with_overrides(self) ->dict:
        return self._get_dict_of_items_with_overrides_for_type(instrument_overrides)

    def _update_override(self, override_type:str, key:str, new_override_object:Override):
        raise NotImplementedError

    def _get_override_object_for_type_and_key(self, override_type:str, key:str) ->Override:
        raise NotImplementedError

    def _get_dict_of_items_with_overrides_for_type(self, override_type: str) -> dict:
        raise NotImplementedError

def _key_from_instrument_strategy(instrument_strategy: instrumentStrategy):
    return instrument_strategy.strategy_name + "/" + instrument_strategy.instrument_code