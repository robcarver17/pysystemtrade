"""
Generate orders for strategies

These are 'virtual' orders, not contract specific

This is a 'run' module, designed to run all day and then stop at the end of the day
FIX ME: At the moment it will only run once

"""

from sysexecution.strategy_order_handling import orderHandlerAcrossStrategies

from syslogdiag.log import logToMongod as logger
from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob

def run_strategy_order_generator():
    with mongoDb() as mongo_db, \
            logger("run_strategy_order_generator", mongo_db=mongo_db) as log:

        data = dataBlob(mongo_db=mongo_db, log=log)

        # FIX ME CODE TO RUN MULTIPLE TIMES
        order_handler = orderHandlerAcrossStrategies(data)
        order_handler.check_for_orders_across_strategies()
