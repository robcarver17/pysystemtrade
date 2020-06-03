"""
Update historical data per contract from interactive brokers data, dump into mongodb
"""


from sysbrokers.IB.ibConnection import connectionIB

from syscore.objects import success, failure, data_error

from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob
from syslogdiag.log import logToMongod as logger
from syslogdiag.emailing import send_mail_msg
from sysdata.private_config import get_private_then_default_key_value

def update_historical_prices():
    """
    Do a daily update for futures contract prices, using IB historical data

    :return: Nothing
    """
    with mongoDb() as mongo_db,\
        logger("Update-Historical-prices", mongo_db=mongo_db) as log,\
        connectionIB(mongo_db = mongo_db, log=log.setup(component="IB-connection")) as ib_conn:

        data = dataBlob("ibFuturesContractPriceData arcticFuturesContractPriceData \
         arcticFuturesMultiplePricesData mongoFuturesContractData",
                        mongo_db = mongo_db, log = log, ib_conn = ib_conn)

        list_of_codes_all = data.arctic_futures_multiple_prices.get_list_of_instruments()
        for instrument_code in list_of_codes_all:
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
    intraday_frequency = get_private_then_default_key_value("intraday_frequency")
    result = get_and_add_prices_for_frequency(data, log, contract_object, frequency=intraday_frequency)
    if result is failure:
        # Skip daily data if intraday not working
        return failure

    result = get_and_add_prices_for_frequency(data, log, contract_object, frequency="D")

    return result

def get_and_add_prices_for_frequency(data, log, contract_object, frequency="D"):
    try:
        ib_prices = data.ib_futures_contract_price.get_prices_at_frequency_for_contract_object(contract_object, frequency)
        rows_added = data.arctic_futures_contract_price.update_prices_for_contract(contract_object, ib_prices,
                                                                                   check_for_spike=True)
        if rows_added is data_error:
            ## SPIKE
            ## Need to email user about this as will need manually checking
            msg = "Spike found in prices for %s: need to manually check by running update_manual_check_historical_prices" % str(
                contract_object)
            log.warn(msg)
            try:
                send_mail_msg(msg, "Price Spike")
            except:
                log.warn("Couldn't send email about price spike for %s" % str(contract_object))

            return failure

        log.msg("Added %d rows at frequency %s for %s" % (rows_added, frequency, str(contract_object)))
        return success

    except Exception as e:
        log.warn("Exception %s when getting data at frequency %s for %s" % (e, frequency, str(contract_object)))
        return failure
