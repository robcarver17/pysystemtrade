"""
Update multiple and adjusted prices

We do this together, to ensure consistency

Two types of services:
- bulk, run after end of day data
- listener, run constantly as data is sampled
- the

"""

from syscore.objects import success

from sysobjects.dict_of_named_futures_per_contract_prices import dictNamedFuturesContractFinalPrices, \
    dictFuturesNamedContractFinalPricesWithContractID

from sysdata.futures.adjusted_prices import no_update_roll_has_occured

from sysproduction.data.get_data import dataBlob
from sysproduction.data.prices import diagPrices, updatePrices


def update_multiple_adjusted_prices():
    """
    Do a daily update for multiple and adjusted prices

    :return: Nothing
    """

    with dataBlob(log_name="Update-Multiple-Adjusted-Prices") as data:
        update_multiple_adjusted_prices_object = updateMultipleAdjustedPrices(
            data)
        update_multiple_adjusted_prices_object.update_multiple_adjusted_prices()

    return success


class updateMultipleAdjustedPrices(object):
    def __init__(self, data):
        self.data = data

    def update_multiple_adjusted_prices(self):
        data = self.data
        diag_prices = diagPrices(data)

        list_of_codes_all = diag_prices.get_list_of_instruments_in_multiple_prices()
        for instrument_code in list_of_codes_all:
            try:

                update_multiple_adjusted_prices_for_instrument(
                    instrument_code, data)
            except Exception as e:
                data.log.warn(
                    "ERROR: Multiple price update went wrong: %s" %
                    str(e))


def update_multiple_adjusted_prices_for_instrument(instrument_code, data):
    """
    Update for multiple and adjusted prices for a given instrument

    :param instrument_code:
    :param data: dataBlob
    :param log: logger
    :return: None
    """

    log = data.log.setup(instrument_code=instrument_code)
    diag_prices = diagPrices(data)
    update_prices = updatePrices(data)
    # update multiple prices with new prices
    # (method in multiple prices object and possible in data socket)
    existing_adjusted_prices = diag_prices.get_adjusted_prices(instrument_code)
    existing_multiple_prices = diag_prices.get_multiple_prices(instrument_code)

    relevant_contracts = existing_multiple_prices.current_contract_dict()

    new_prices_dict = get_dict_of_new_prices_and_contractid(
        instrument_code, relevant_contracts, data
    )
    updated_multiple_prices = existing_multiple_prices.update_multiple_prices_with_dict(
        new_prices_dict)

    updated_adjusted_prices = (
        existing_adjusted_prices.update_with_multiple_prices_no_roll(
            updated_multiple_prices
        )
    )

    if updated_adjusted_prices is no_update_roll_has_occured:
        log.critical(
            "Can't update adjusted prices for %s as roll has occured but not registered properly" %
            instrument_code)
        raise Exception()

    update_prices.add_multiple_prices(
        instrument_code, updated_multiple_prices, ignore_duplication=True
    )
    update_prices.add_adjusted_prices(
        instrument_code, updated_adjusted_prices, ignore_duplication=True
    )

    return success


def get_dict_of_new_prices_and_contractid(
        instrument_code, contract_date_dict, data):
    """

    :param instrument_code: str
    :param contract_list: dict of 'yyyymmdd' str, keynames 'CARRY, PRICE, FORWARD'
    :param data:
    :return: dict of futures contract prices for each contract, plus contract id column
    """
    diag_prices = diagPrices(data)
    # get prices for relevant contracts, return as dict labelled with column
    # for contractids
    relevant_contract_prices = dict()
    for key, contract_date in contract_date_dict.items():
        price_series = diag_prices.get_prices_for_instrument_code_and_contract_date(
            instrument_code, contract_date)
        relevant_contract_prices[key] = price_series.return_final_prices()

    relevant_contract_prices = dictNamedFuturesContractFinalPrices(relevant_contract_prices)

    new_prices_dict = (
        dictFuturesNamedContractFinalPricesWithContractID.create_from_two_dicts(
            relevant_contract_prices, contract_date_dict
        )
    )

    return new_prices_dict
