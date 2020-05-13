
from sysbrokers.IB.ibConnection import connectionIB

from syscore.objects import success, failure

from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob
from sysproduction.data.capital import dataCapital
from syslogdiag.log import logToMongod as logger
from syslogdiag.emailing import send_mail_msg


def update_account_values():
    """
    Do a daily update of accounting information

    Get the total account value from IB, and calculate the p&l since we last ran

    This calculation is done using a user specified handler, which can deal with eg multiple accounts if required

    Needs to know about any withdrawals.

    Does spike checking: large changes in account value are checked before writing

    If your strategy has very high risk you may wish to do this more frequently than daily

    :return: Nothing
    """
    with mongoDb() as mongo_db,\
        logger("Update-Account-Values", mongo_db=mongo_db) as log,\
        connectionIB(mongo_db = mongo_db, log=log.setup(component="IB-connection")) as ib_conn:

        data = dataBlob(mongo_db = mongo_db, log = log, ib_conn = ib_conn)

        capital_data = dataCapital(data)

        ## This assumes that each account only reports eithier in one currency or for each currency, i.e. no double counting
        total_account_value_in_base_currency = capital_data.get_ib_total_capital_value()
        log.msg("Broker account value is %f" % total_account_value_in_base_currency)

        # Update total capital
        try:
            new_capital = capital_data.total_capital_calculator.\
                get_total_capital_with_new_broker_account_value(total_account_value_in_base_currency)
        except Exception as e:
            ## Problem, most likely spike
            log.critical("Error %s whilst updating total capital; you may have to use update_capital_manual script or function" % e)
            return failure

        log.msg("New capital is %f" % new_capital)


    return success
