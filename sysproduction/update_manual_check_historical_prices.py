"""
Update historical data per contract from interactive brokers data, dump into mongodb

Apply a check to each price series
"""


from sysbrokers.IB.ibConnection import connectionIB

from syscore.objects import success, failure

from sysdata.mongodb.mongo_connection import mongoDb
from sysproduction.data.get_data import dataBlob
from sysdata.futures.manual_price_checker import manual_price_checker
from sysdata.futures.futures_per_contract_prices import futuresContractPrices
from syslogdiag.log import logToMongod as logger
from sysdata.private_config import get_private_then_default_key_value

def update_manual_check_historical_prices(instrument_code:str):
    """
    Do a daily update for futures contract prices, using IB historical data

    If any 'spikes' are found, run manual checks

    :return: Nothing
    """
    with mongoDb() as mongo_db,\
        logger("Update-Historical-prices-manually", mongo_db=mongo_db) as log,\
        connectionIB(mongo_db = mongo_db, log=log.setup(component="IB-connection")) as ib_conn:

        data = dataBlob("ibFuturesContractPriceData arcticFuturesContractPriceData \
         arcticFuturesMultiplePricesData mongoFuturesContractData",
                        mongo_db = mongo_db, log = log, ib_conn = ib_conn)

        list_of_codes_all = data.arctic_futures_contract_price.get_instruments_with_price_data()
        if instrument_code not in list_of_codes_all:
            print("\n\n\ %s is not an instrument with price data \n\n" % instrument_code)
            raise Exception()
        update_historical_prices_with_checks_for_instrument(instrument_code, data, log=log.setup(instrument_code = instrument_code))

    return success


def update_historical_prices_with_checks_for_instrument(instrument_code, data, log=logger("")):
    """
    Do a daily update for futures contract prices, using IB historical data

    Any 'spikes' are manually checked

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
        update_historical_prices_with_checks_for_instrument_and_contract(contract_object, data,
                                                             log=log.setup(contract_date = contract_object.date))

    return success

def update_historical_prices_with_checks_for_instrument_and_contract(contract_object, data, log=logger("")):
    """
    Do a daily update for futures contract prices, using IB historical data, with checking

    :param contract_object: futuresContract
    :param data: data blob
    :param log: logger
    :return: None
    """
    intraday_frequency = get_private_then_default_key_value("intraday_frequency")
    get_and_check_prices_for_frequency(data, log, contract_object, frequency=intraday_frequency)
    get_and_check_prices_for_frequency(data, log, contract_object, frequency="D")

    return success

def get_and_check_prices_for_frequency(data, log, contract_object, frequency="D"):
    try:
        old_prices = data.arctic_futures_contract_price.get_prices_for_contract_object(contract_object)
        ib_prices = data.ib_futures_contract_price.get_prices_at_frequency_for_contract_object(contract_object, frequency)
        if len(ib_prices) == 0:
            raise Exception("No IB prices found for %s nothing to check" % str(contract_object))

        print("\n\n Manually checking prices for %s \n\n" % str(contract_object))
        new_prices_checked = manual_price_checker(old_prices, ib_prices,
                                                  column_to_check='FINAL',
                                                  delta_columns=['OPEN', 'HIGH', 'LOW'],
                                                  type_new_data=futuresContractPrices
                                                  )
        result = data.arctic_futures_contract_price.update_prices_for_contract(contract_object, new_prices_checked,
                                                                                   check_for_spike=False)
        return result

    except Exception as e:
        log.warn("Exception %s when getting or checking data at frequency %s for %s" % (e, frequency, str(contract_object)))
        return failure

