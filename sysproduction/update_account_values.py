"""
Update historical data per contract from interactive brokers data, dump into mongodb
"""


from sysbrokers.IB.ibConnection import connectionIB

from syscore.objects import success, failure, data_error

from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob
from sysproduction.data.currency_data import currencyData
from syslogdiag.log import logToMongod as logger
from syslogdiag.emailing import send_mail_msg


def update_account_values():
    """
    Do a daily update of accounting information

    Get the total account value from IB, and calculate the p&l since we last ran

    This calculation is done using a user specified handler, which can deal with eg multiple accounts if required

    Needs to know about any withdrawals.

    Does spike checking: large changes in account value are checked before writing

    Also get various other capital information

accountValues
accountSummary
portfolio
positions

reqPnL
pnl
cancelPnL

reqPnLSingle
pnlSingle
cancelPnLSingle

    All of this is passed to a single capital allocator function that calculates how much capital each strategy should be allocated
      and works out the p&l for each strategy

    This can be done in various ways, eg by instrument, by asset class, as a % of total account value
       ... allow each strategy to keep it's p&l, or redistribute

    What about margin? Might need to know 'in real time' what the margin is per strategy, if when
       using whatif trades need to check. However better doing this on a global basis for account


    If your strategy has very high risk you may wish to do this more frequently than daily

    :return: Nothing
    """
    with mongoDb() as mongo_db,\
        logger("Update-Historical-prices", mongo_db=mongo_db) as log,\
        connectionIB(mongo_db = mongo_db, log=log.setup(component="IB-connection")) as ib_conn:

        data = dataBlob("ibFuturesContractPriceData arcticFuturesContractPriceData \
         arcticFuturesMultiplePricesData mongoFuturesContractData",
                        mongo_db = mongo_db, log = log, ib_conn = ib_conn)



        currency_data = currencyData(data)
        values_across_accounts = data.ib_conn.broker_get_account_value_across_currency_across_accounts()

        ## This assumes that each account only reports eithier in one currency or for each currency, i.e. no double counting
        total_account_value_in_base_currency = currency_data.total_of_list_of_currency_values_in_base(values_across_accounts)

    return success
