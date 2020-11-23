"""
Update historical data per contract from interactive brokers data, dump into mongodb

Apply a check to each price series
"""

from syscore.objects import success, failure

from sysdata.futures.futures_per_contract_prices import DAILY_PRICE_FREQ
from sysproduction.data.get_data import dataBlob
from sysproduction.data.prices import (
    diagPrices,
    updatePrices,
    get_valid_instrument_code_from_user,
)
from sysproduction.data.broker import dataBroker
from sysproduction.data.contracts import diagContracts
from sysdata.futures.manual_price_checker import manual_price_checker
from sysobjects.futures_per_contract_prices import futuresContractPrices
from sysobjects.contracts import futuresContract

def interactive_manual_check_historical_prices(instrument_code: str):
    """
    Do a daily update for futures contract prices, using IB historical data

    If any 'spikes' are found, run manual checks

    :return: Nothing
    """
    with dataBlob(log_name="Update-Historical-prices-manually") as data:
        instrument_code = get_valid_instrument_code_from_user(data)
        check_instrument_ok_for_broker(data, instrument_code)
        data.log.label(instrument_code = instrument_code)
        update_historical_prices_with_checks_for_instrument(
            instrument_code, data)

    return success

def check_instrument_ok_for_broker(data: dataBlob, instrument_code: str):
    diag_prices = diagPrices(data)
    list_of_codes_all = diag_prices.get_list_of_instruments_with_contract_prices()
    if instrument_code not in list_of_codes_all:
        print(
            "\n\n\ %s is not an instrument with price data \n\n" %
            instrument_code)
        raise Exception()


def update_historical_prices_with_checks_for_instrument(
        instrument_code: str, data: dataBlob):
    """
    Do a daily update for futures contract prices, using IB historical data

    Any 'spikes' are manually checked

    :param instrument_code: str
    :param data: dataBlob
    :return: None
    """
    diag_contracts = diagContracts(data)
    all_contracts_list = diag_contracts.get_all_contract_objects_for_instrument_code(
        instrument_code)
    contract_list = all_contracts_list.currently_sampling()

    if len(contract_list) == 0:
        data.log.warn("No contracts marked for sampling for %s" % instrument_code)
        return failure

    for contract_object in contract_list:
        data.log.label(contract_date=contract_object.date_str)
        update_historical_prices_with_checks_for_instrument_and_contract(
            contract_object, data)

    return success


def update_historical_prices_with_checks_for_instrument_and_contract(
    contract_object: futuresContract, data: dataBlob):
    """
    Do a daily update for futures contract prices, using IB historical data, with checking

    :param contract_object: futuresContract
    :param data: data blob
    :param log: logger
    :return: None
    """
    diag_prices = diagPrices(data)
    intraday_frequency = diag_prices.get_intraday_frequency_for_historical_download()
    daily_frequency = DAILY_PRICE_FREQ

    get_and_check_prices_for_frequency(
        data, contract_object, frequency=intraday_frequency
    )
    get_and_check_prices_for_frequency(
        data, contract_object, frequency=daily_frequency)

    return success


def get_and_check_prices_for_frequency(
        data: dataBlob, contract_object: futuresContract, frequency="D"):

    broker_data = dataBroker(data)
    price_data = diagPrices(data)
    price_updater = updatePrices(data)

    old_prices = price_data.get_prices_for_contract_object(contract_object)

    broker_prices = broker_data.get_prices_at_frequency_for_contract_object(
        contract_object, frequency
    )
    if len(broker_prices) == 0:
        print(
            "No broker prices found for %s nothing to check" %
            str(contract_object))
        return failure

    print(
        "\n\n Manually checking prices for %s \n\n" %
        str(contract_object))
    new_prices_checked = manual_price_checker(
        old_prices,
        broker_prices,
        column_to_check="FINAL",
        delta_columns=["OPEN", "HIGH", "LOW"],
        type_new_data=futuresContractPrices,
    )
    price_updater.update_prices_for_contract(
        contract_object, new_prices_checked, check_for_spike=False
    )
