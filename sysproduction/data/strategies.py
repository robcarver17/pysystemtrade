from sysdata.data_blob import dataBlob
from syscore.objects import missing_data, arg_not_supplied
from syscore.interactive import print_menu_of_values_and_get_response
from sysproduction.data.positions import diagPositions, dataOptimalPositions

from sysproduction.data.generic_production_data import productionDataLayerGeneric

class diagStrategiesConfig(productionDataLayerGeneric):
    ## doesn't use anything in data class just accessses config

    def get_strategy_config_dict_for_specific_process(self, strategy_name: str,
                                                      process_name: str) -> dict:
        this_strategy_dict= self.get_strategy_config_dict_for_strategy(strategy_name)
        process_dict = this_strategy_dict.get(process_name, {})

        return process_dict

    def get_strategy_config_dict_for_strategy(self, strategy_name: str) -> dict:
        strategy_dict = self.get_all_strategy_dict()
        if strategy_dict is missing_data:
                raise Exception("strategy_list not defined in defaults.yaml or private yaml config!")
        this_strategy_dict = strategy_dict[strategy_name]

        return this_strategy_dict

    def get_list_of_strategies(self) -> list:
        strategy_dict = self.get_all_strategy_dict()
        if strategy_dict is missing_data:
                raise Exception("strategy_list not defined in defaults.yaml or private yaml config!")
        list_of_strategies = list(strategy_dict.keys())

        return list_of_strategies

    def get_strategy_allocation_config_dict(self) -> dict:
        config = self.data.config
        strategy_allocation_dict = config.get_element_or_missing_data("strategy_capital_allocation")

        return strategy_allocation_dict

    def get_all_strategy_dict(self) -> dict:
        config = self.data.config
        strategy_dict = config.get_element_or_missing_data("strategy_list")

        return strategy_dict


def get_list_of_strategies(data: dataBlob=arg_not_supplied, source="config") -> list:
    if source=="config":
        return get_list_of_strategies_from_config(data)
    elif source=="positions":
        return get_list_of_strategies_from_positions(data)
    elif source=="optimal_positions":
        return get_list_of_strategies_from_optimal_positions(data)
    else:
        raise Exception("Source %s not recognised!" % source)

def get_list_of_strategies_from_config(data: dataBlob=arg_not_supplied) -> list:
    diag_strategies_config = diagStrategiesConfig(data)
    list_of_strategies = diag_strategies_config.get_list_of_strategies()

    return list_of_strategies

def get_list_of_strategies_from_positions(data: dataBlob=arg_not_supplied) -> list:
    diag_positions = diagPositions(data)
    list_of_strategies = diag_positions.get_list_of_strategies_with_positions()

    return list_of_strategies

def get_list_of_strategies_from_optimal_positions(data: dataBlob = arg_not_supplied) -> list:
    data_optimal_positions = dataOptimalPositions(data)
    list_of_strategies = data_optimal_positions.get_list_of_strategies_with_optimal_position()

    return list_of_strategies

def get_valid_strategy_name_from_user(
    data: dataBlob=arg_not_supplied,
        allow_all: bool=False,
        all_code:str="ALL",
        source: str="config"
):
    all_strategies = get_list_of_strategies(data=data, source=source)
    if allow_all:
        default_strategy = all_code
    else:
        default_strategy = all_strategies[0]

    strategy_name = print_menu_of_values_and_get_response(all_strategies, default_str=default_strategy)

    return strategy_name


