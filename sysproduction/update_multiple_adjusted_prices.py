"""
Update multiple and adjusted prices

We do this together, to ensure consistency

Two types of services:
- bulk, run after end of day data
- listener, run constantly as data is sampled
- the

"""

from collections import namedtuple

from syscore.objects import success

from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData
from sysdata.futures.futures_per_contract_prices import dictFuturesContractFinalPricesWithContractID
from sysdata.mongodb.mongo_connection import mongoDb

from syslogdiag.log import logToMongod as logger

DataBlob = namedtuple("DataBlob", "per_contract_prices multiple_prices adjusted_prices")


def update_multiple_adjusted_prices_daily():
    """
    Do a daily update for multiple and adjusted prices

    :return: Nothing
    """

    """
    mongo_db = mongoDb()
    log=logger("Update-multiple-adjusted-prices(daily)", mongo_db=mongo_db)
    """
    with mongoDb() as mongo_db, \
            logger("Update-multiple-adjusted-prices(daily)", mongo_db=mongo_db) as log:

        data = setup_data(mongo_db, log=log)

        list_of_codes_all = data.multiple_prices.get_list_of_instruments()
        for instrument_code in list_of_codes_all:
            update_multiple_adjusted_prices_for_instrument(instrument_code, data,
                                                           log=log.setup(instrument_code = instrument_code))


    return success

def setup_data(mongo_db, log=logger("")):
    arctic_per_contract_prices = arcticFuturesContractPriceData(mongo_db=mongo_db,
                                                                log=log.setup(
                                                                    component="arcticFuturesContractPriceData"))
    arctic_multiple_prices = arcticFuturesMultiplePricesData(mongo_db=mongo_db,
                                                             log=log.setup(component="arcticFuturesMultiplePricesData"))
    arctic_adjusted_prices = arcticFuturesAdjustedPricesData(mongo_db=mongo_db,
                                                             log=log.setup(component="arcticFuturesAdjustedPricesData"))

    data = DataBlob(per_contract_prices=arctic_per_contract_prices,
                    multiple_prices=arctic_multiple_prices,
                    adjusted_prices=arctic_adjusted_prices)

    return data

def update_multiple_adjusted_prices_for_instrument(instrument_code, data, log=logger("")):
    """
    Update for multiple and adjusted prices for a given instrument

    :param instrument_code:
    :param data: dataBlob
    :param log: logger
    :return: None
    """

    existing_adjusted_prices = data.adjusted_prices.get_adjusted_prices(instrument_code)
    existing_multiple_prices = data.multiple_prices.get_multiple_prices(instrument_code)

    relevant_contracts = existing_multiple_prices.current_contract_dict()

    new_prices_dict = get_dict_of_new_prices_and_contractid(instrument_code, relevant_contracts, data)

    # update multiple prices with new prices
    # (method in multiple prices object and possible in data socket)


    ## LISTENER PROTOCOL
    ## shared data blob
    ## threads one per instrument
    ## check

def get_dict_of_new_prices_and_contractid(instrument_code, contract_date_dict, data):
    """

    :param instrument_code: str
    :param contract_list: dict of 'yyyymmdd' str, keynames 'CARRY, PRICE, FORWARD'
    :param data:
    :return: dict of futures contract prices for each contract, plus contract id column
    """
    # get prices for relevant contracts, return as dict labelled with column for contractids
    relevant_contract_prices = dict()
    for key, contract_date in contract_date_dict.items():
        price_series = data.per_contract_prices.\
                get_prices_for_instrument_code_and_contract_date(instrument_code, contract_date)
        relevant_contract_prices[key] = price_series.return_final_prices()

    new_prices_dict = dictFuturesContractFinalPricesWithContractID.\
        create_from_two_dicts(relevant_contract_prices, contract_date_dict)

    return new_prices_dict

