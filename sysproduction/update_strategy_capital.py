from copy import copy
import datetime

from syscore.exceptions import missingData
from syscore.constants import success

from sysdata.data_blob import dataBlob
from sysproduction.data.capital import dataCapital, dataMargin
from sysproduction.data.strategies import diagStrategiesConfig

from syscore.objects import resolve_function


def update_strategy_capital():
    """
    Allocate capital to different strategies

    :return: Nothing
    """
    with dataBlob(log_name="Update-Strategy-Capital") as data:
        update_strategy_capital_object = updateStrategyCapital(data)
        update_strategy_capital_object.strategy_allocation()

    return success


class updateStrategyCapital(object):
    def __init__(self, data: dataBlob):
        self.data = data

    def strategy_allocation(self):
        self.capital_strategy_allocation()
        self.margin_strategy_allocation()

    def capital_strategy_allocation(self):
        """
        Used to allocate capital to strategies. Doesn't actually do the allocation but get's from another function,
          defined in config.strategy_capital_allocation.function (defaults.yaml, or overide in private_config.yaml)

        Writes the result to capital data, which is then picked up by run strategy

        :param data: A data blob
        :return: None
        """
        try:
            data = self.data
            total_capital = get_total_current_capital(data)
            strategy_capital_dict = call_allocation_function(
                data, capital_to_allocate=total_capital
            )
            write_allocated_strategy_capital(data, strategy_capital_dict)
        except Exception as e:
            # Problem, will send email
            self.data.log.critical("Error [%s] whilst allocating strategy capital" % e)

        return None

    def margin_strategy_allocation(self):
        try:
            data = self.data
            total_margin = get_total_current_margin(data)
            strategy_margin_dict = call_allocation_function(
                data, capital_to_allocate=total_margin
            )
            write_allocated_strategy_margin(data, strategy_margin_dict)
        except Exception as e:
            # Problem, will send email
            self.data.log.critical("Error [%s] whilst allocating strategy margin" % e)

        return None


def get_total_current_capital(data: dataBlob) -> float:
    data_capital = dataCapital(data)
    try:
        total_capital = data_capital.get_current_total_capital()
    except missingData:
        data.log.critical("Can't allocate strategy capital without total capital")
        raise

    return total_capital


def get_total_current_margin(data: dataBlob) -> float:
    data_margin = dataMargin(data)
    try:
        total_margin = data_margin.get_current_total_margin()
    except missingData:
        data.log.critical("Can't allocate strategy margin without total margin")
        raise

    return total_margin


def call_allocation_function(data: dataBlob, capital_to_allocate: float) -> dict:

    strategy_allocation_config_dict = get_strategy_allocation_config_dict(data)

    strategy_allocation_function_str = strategy_allocation_config_dict.pop("function")
    strategy_allocation_function = resolve_function(strategy_allocation_function_str)

    results = strategy_allocation_function(
        data, capital_to_allocate=capital_to_allocate, **strategy_allocation_config_dict
    )

    return results


def get_strategy_allocation_config_dict(data: dataBlob) -> dict:
    config = diagStrategiesConfig(data)
    allocation_dict = config.get_strategy_allocation_config_dict()
    allocation_dict_copy = copy(allocation_dict)
    return allocation_dict_copy


def write_allocated_strategy_capital(data: dataBlob, strategy_capital_dict: dict):
    capital_data = dataCapital(data)
    date = datetime.datetime.now()
    for strategy_name, strategy_capital in strategy_capital_dict.items():
        capital_data.update_capital_value_for_strategy(
            strategy_name, strategy_capital, date=date
        )
        data.log.msg(
            "Updated capital for %s to %f" % (strategy_name, strategy_capital),
            strategy_name=strategy_name,
        )


def write_allocated_strategy_margin(data: dataBlob, strategy_margin_dict: dict):
    margin_data = dataMargin(data)
    for strategy_name, strategy_margin in strategy_margin_dict.items():
        margin_data.add_strategy_margin_entry(
            strategy_name=strategy_name, margin_entry=strategy_margin
        )

        data.log.msg(
            "Updated margin for %s to %f" % (strategy_name, strategy_margin),
            strategy_name=strategy_name,
        )


if __name__ == "__main__":
    update_strategy_capital()
