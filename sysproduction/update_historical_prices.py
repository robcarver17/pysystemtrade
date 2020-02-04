"""
Update historical data per contract from interactive brokers data, dump into mongodb
"""

from collections import namedtuple

from sysbrokers.IB.ibConnection import connectionIB
from sysbrokers.IB.ibFuturesContractPriceData import ibFuturesContractPriceData

from syscore.objects import success, failure

from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.mongodb.mongo_futures_contracts import mongoFuturesContractData
from sysdata.mongodb.mongo_connection import mongoDb

from syslogdiag.log import logToMongod as logger

dataBlob = namedtuple("DataBlob", "ib_pricedata arctic_pricedata arctic_multiple_price_data mongo_contractsdata ib_conn")


def update_historical_prices():
    """
    Do a daily update for futures contract prices, using IB historical data

    :return: Nothing
    """
    with mongoDb() as mongo_db,\
        logger("Update-Historical-prices", mongo_db=mongo_db) as log,\
        connectionIB(log=log.setup(component="IB-connection")) as ib_conn:

        data = setup_data(mongo_db, ib_conn, log=log)

        list_of_codes_all = data.arctic_multiple_price_data.get_list_of_instruments()
        for instrument_code in list_of_codes_all:
            update_historical_prices_for_instrument(instrument_code, data, log=log.setup(instrument_code = instrument_code))


    return success

def setup_data(mongo_db, ib_conn, log=logger("")):

    ib_pricedata = ibFuturesContractPriceData(ib_conn, log=log.setup(component="IB-price-data"))
    arctic_pricedata = arcticFuturesContractPriceData(mongo_db=mongo_db,
                                                      log=log.setup(component="arcticFuturesContractPriceData"))
    mongo_contractsdata = mongoFuturesContractData(mongo_db=mongo_db,
                                                   log = log.setup(component="mongoFuturesContractData"))

    arctic_multiple_price_data = arcticFuturesMultiplePricesData(mongo_db=mongo_db,
                                                                 log = log.setup(component="arcticFuturesMultiplePricesData"))

    data = dataBlob(ib_pricedata = ib_pricedata, arctic_pricedata = arctic_pricedata,
                    arctic_multiple_price_data = arctic_multiple_price_data,
                    mongo_contractsdata = mongo_contractsdata, ib_conn = ib_conn)


    return data


def update_historical_prices_for_instrument(instrument_code, data, log=logger("")):
    """
    Do a daily update for futures contract prices, using IB historical data

    :param instrument_code: str
    :param data: dataBlob
    :param log: logger
    :return: None
    """

    all_contracts_list = data.mongo_contractsdata.get_all_contract_objects_for_instrument_code(instrument_code)
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
    ib_prices = data.ib_pricedata.get_prices_for_contract_object(contract_object)
    if len(ib_prices)==0:
        log.warn("No IB prices found for %s" % str(contract_object))
        return failure

    data.arctic_pricedata.update_prices_for_contract(contract_object, ib_prices)

    return success