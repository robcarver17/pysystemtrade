import datetime
import socket

from sysdata.data_blob import dataBlob
from sysdata.private_config import get_private_then_default_key_value
from syscore.objects import arg_not_supplied
from syscore.genutils import print_menu_of_values_and_get_response


class diagStrategiesConfig(object):
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()
        self.data = data

    def get_strategy_dict_for_strategy(self, strategy_name):
        strategy_dict = self.get_all_strategy_dict()
        this_strategy_dict = strategy_dict[strategy_name]

        return this_strategy_dict

    def get_list_of_strategies(self):
        strategy_dict = self.get_all_strategy_dict()
        return list(strategy_dict.keys())

    def get_strategy_allocation_config_dict(self):
        strategy_allocation_dict = getattr(
            self, "_strategy_allocation_dict", None)
        if strategy_allocation_dict is None:
            self._strategy_allocation_dict = (
                strategy_allocation_dict
            ) = get_private_then_default_key_value("strategy_capital_allocation")

        return strategy_allocation_dict

    def get_all_strategy_dict(self):
        strategy_dict = getattr(self, "_strategy_dict", None)
        if strategy_dict is None:
            self._strategy_dict = strategy_dict = get_private_then_default_key_value(
                "strategy_list")

        return strategy_dict


def get_list_of_strategies(data=arg_not_supplied):
    d = diagStrategiesConfig(data)
    return d.get_list_of_strategies()


def get_valid_strategy_name_from_user(
    data=arg_not_supplied, allow_all=False, all_code="ALL"
):
    all_strategies = get_list_of_strategies(data=data)
    if allow_all:
        default_strategy = all_code
    else:
        default_strategy = all_strategies[0]
    strategy_name = print_menu_of_values_and_get_response(all_strategies, default_str=default_strategy)

    return strategy_name

