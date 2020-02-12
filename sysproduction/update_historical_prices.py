"""
Update historical data per contract from interactive brokers data, dump into mongodb
"""


from sysbrokers.IB.ibConnection import connectionIB

from syscore.objects import success, failure

from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob
from syslogdiag.log import logToMongod as logger


def update_historical_prices():
    """
    Do a daily update for futures contract prices, using IB historical data

    :return: Nothing
    """
    with mongoDb() as mongo_db,\
        logger("Update-Historical-prices", mongo_db=mongo_db) as log,\
        connectionIB(log=log.setup(component="IB-connection")) as ib_conn:

        data = dataBlob("ibFuturesContractPriceData arcticFuturesContractPriceData \
         arcticFuturesMultiplePricesData mongoFuturesContractData",
                        mongo_db = mongo_db, log = log, ib_conn = ib_conn)

        list_of_codes_all = data.arctic_futures_multiple_prices.get_list_of_instruments()
        for instrument_code in ["CRUDE_W"]:
            update_historical_prices_for_instrument(instrument_code, data, log=log.setup(instrument_code = instrument_code))


    return success


def update_historical_prices_for_instrument(instrument_code, data, log=logger("")):
    """
    Do a daily update for futures contract prices, using IB historical data

    :param instrument_code: str
    :param data: dataBlob
    :param log: logger
    :return: None
    """

    all_contracts_list = data.mongo_futures_contract.get_all_contract_objects_for_instrument_code(instrument_code)
    contract_list = all_contracts_list.currently_sampling()

    if len(contract_list)==0:
        log.warn("No contracts marked for sampling for %s" % instrument_code)
        return failure

    for contract_object in contract_list:
        update_historical_prices_for_instrument_and_contract(contract_object, data,
                                                             log=log.setup(contract_date = contract_object.date))

    return success

def update_historical_prices_for_instrument_and_contract(contract_object, data, log=logger("")):
    """
    Do a daily update for futures contract prices, using IB historical data

    :param contract_object: futuresContract
    :param data: data blob
    :param log: logger
    :return: None
    """
    ib_prices = data.ib_futures_contract_price.get_prices_for_contract_object(contract_object)
    if len(ib_prices)==0:
        log.warn("No IB prices found for %s" % str(contract_object))
        return failure

    data.arctic_futures_contract_price.update_prices_for_contract(contract_object, ib_prices)

    return success

update_historical_prices()
