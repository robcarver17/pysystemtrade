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
from sysdata.futures.adjusted_prices import no_update_roll_has_occured
from sysdata.mongodb.mongo_connection import mongoDb

from syslogdiag.log import logToMongod as logger

DataBlob = namedtuple("DataBlob", "per_contract_prices multiple_prices adjusted_prices")


def update_multiple_adjusted_prices_daily():
    """
    Do a daily update for multiple and adjusted prices

    :return: Nothing
    """

    with mongoDb() as mongo_db, \
            logger("Update-multiple-adjusted-prices(daily)", mongo_db=mongo_db) as log:

        data = setup_data(mongo_db, log=log)

        list_of_codes_all = data.multiple_prices.get_list_of_instruments()
        for instrument_code in list_of_codes_all:
            try:

                update_multiple_adjusted_prices_for_instrument(instrument_code, data,
                                                           log=log.setup(instrument_code = instrument_code))
            except Exception as e:
                log.warn("Multiple price update %s went wrong" % e)


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

    # update multiple prices with new prices
    # (method in multiple prices object and possible in data socket)
    existing_adjusted_prices = data.adjusted_prices.get_adjusted_prices(instrument_code)
    existing_multiple_prices = data.multiple_prices.get_multiple_prices(instrument_code)

    relevant_contracts = existing_multiple_prices.current_contract_dict()

    new_prices_dict = get_dict_of_new_prices_and_contractid(instrument_code, relevant_contracts, data)
    updated_multiple_prices = existing_multiple_prices.update_multiple_prices_with_dict(new_prices_dict)

    updated_adjusted_prices = existing_adjusted_prices.update_with_multiple_prices_no_roll(updated_multiple_prices)

    if updated_multiple_prices is no_update_roll_has_occured:
        raise Exception("Can't update adjusted prices as roll has occured but not registered properly")

    data.multiple_prices.add_multiple_prices(instrument_code, updated_multiple_prices, ignore_duplication=True)
    data.adjusted_prices.add_adjusted_prices(instrument_code, updated_adjusted_prices, ignore_duplication=True)

    return success

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

