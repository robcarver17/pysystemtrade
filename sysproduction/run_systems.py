"""
Run overnight backtest of systems to generate optimal positions

These are defined in eithier the defaults.yaml file or overriden in private config
strategy_list:
  example:
    overnight_launcher:
      function: sysproduction.example_run_system.run_system
      backtest_config_filename: "systems.provided.futures_chapter15.futures_config.yaml",
      account_currency: "GBP"

"""
from copy import copy

from sysdata.private_config import get_private_then_default_key_value
from syscore.objects import resolve_function

from syslogdiag.log import logToMongod as logger
from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob

def run_systems():
    with mongoDb() as mongo_db, \
            logger("update_run_systems", mongo_db=mongo_db) as log:

        data = dataBlob(mongo_db=mongo_db, log=log)

        strategy_dict = get_private_then_default_key_value('strategy_list')
        for strategy_name in strategy_dict:
            data.log.label(strategy = strategy_name)
            try:
                launch_function, launch_args = _get_launch_config(strategy_dict[strategy_name])
            except Exception as e:
                log.critical("Error %s with config in defaults or private yaml files for strategy_list:%s:overnight_launcher" % (e,strategy_name))

            # By convention, arg is strategy_name, data, kwargs are the rest of config
            try:
                launch_function(strategy_name, data, **launch_args)
            except Exception as e:
                log.critical("Error %s running system for %s" % (e,strategy_name))

def _get_launch_config(config_for_strategy):
    launcher_config = copy(config_for_strategy['overnight_launcher'])
    launch_function = launcher_config.pop('function')
    launch_function = resolve_function(launch_function)

    # what's left is
    launch_args = launcher_config

    return launch_function, launch_args