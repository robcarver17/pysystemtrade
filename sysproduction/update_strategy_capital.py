
import datetime

from sysbrokers.IB.ibConnection import connectionIB

from syscore.objects import success

from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob
from sysproduction.data.capital import dataCapital
from syslogdiag.log import logToMongod as logger

from sysdata.private_config import get_private_then_default_key_value
from syscore.objects import resolve_function


def update_strategy_capital():
    """
    Allocate capital to different strategies

    :return: Nothing
    """
    with mongoDb() as mongo_db,\
        logger("Update-Strategy-Capital", mongo_db=mongo_db) as log,\
        connectionIB(mongo_db = mongo_db, log=log.setup(component="IB-connection")) as ib_conn:

        data = dataBlob(mongo_db = mongo_db, log = log, ib_conn = ib_conn)

        try:
            strategy_allocation(data)
        except Exception as e:
            ## Problem, will send email
            log.critical("Error %s whilst allocating strategy capital" % e)

    return success

def strategy_allocation(data):
    """
    Used to allocate capital to strategies. Doesn't actually do the allocation but get's from another function,
      defined in config.strategy_capital_allocation.function (defaults.yaml, or overide in private_config.yaml)

    Writes the result to capital data, which is then picked up by run strategy

    :param data: A data blob
    :return: success or Exception
    """

    strategy_capital_dict = call_allocation_function(data)
    write_allocated_weights(data, strategy_capital_dict)

    return success


def call_allocation_function(data):

    strategy_allocation_config_dict = get_strategy_allocation_config_dict()
    strategy_allocation_function_str = strategy_allocation_config_dict.pop('function')
    strategy_allocation_function = resolve_function(strategy_allocation_function_str)

    results = strategy_allocation_function(data, **strategy_allocation_config_dict)

    return results

def get_strategy_allocation_config_dict():
    return get_private_then_default_key_value('strategy_capital_allocation')

def write_allocated_weights(data, strategy_capital_dict):
    capital_data = dataCapital(data)
    date = datetime.datetime.now()
    for strategy_name, strategy_capital in strategy_capital_dict.items():
        capital_data.update_capital_value_for_strategy(strategy_name, strategy_capital, date=date)
        data.log.msg("Updated capital for %s to %f" % (strategy_name, strategy_capital))

    return success

