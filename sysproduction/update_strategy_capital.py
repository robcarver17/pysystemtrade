import datetime

from syscore.objects import success

from sysproduction.data.get_data import dataBlob
from sysproduction.data.capital import dataCapital
from sysproduction.data.strategies import diagStrategiesConfig

from sysdata.private_config import get_private_then_default_key_value
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
    def __init__(self, data):
        self.data = data

    def strategy_allocation(self):
        """
        Used to allocate capital to strategies. Doesn't actually do the allocation but get's from another function,
          defined in config.strategy_capital_allocation.function (defaults.yaml, or overide in private_config.yaml)

        Writes the result to capital data, which is then picked up by run strategy

        :param data: A data blob
        :return: None
        """
        try:
            data = self.data
            strategy_capital_dict = call_allocation_function(data)
            write_allocated_weights(data, strategy_capital_dict)
        except Exception as e:
            # Problem, will send email
            self.data.log.critical(
                "Error %s whilst allocating strategy capital" %
                e)

        return None


def call_allocation_function(data):

    strategy_allocation_config_dict = get_strategy_allocation_config_dict(data)
    strategy_allocation_function_str = strategy_allocation_config_dict.pop(
        "function")
    strategy_allocation_function = resolve_function(
        strategy_allocation_function_str)

    results = strategy_allocation_function(
        data, **strategy_allocation_config_dict)

    return results


def get_strategy_allocation_config_dict(data):
    config = diagStrategiesConfig(data)
    return config.get_strategy_allocation_config_dict()


def write_allocated_weights(data, strategy_capital_dict):
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

    return success
