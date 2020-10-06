"""
Update historical data per contract from interactive brokers data, dump into mongodb

Apply a check to each price series
"""

from syscore.objects import success, failure

from sysproduction.data.get_data import dataBlob
from sysproduction.data.prices import (
    diagPrices,
    updatePrices,
    get_valid_instrument_code_from_user,
)
from sysproduction.data.broker import dataBroker
from sysproduction.data.contracts import diagContracts
from sysdata.futures.manual_price_checker import manual_price_checker
from sysdata.futures.futures_per_contract_prices import futuresContractPrices


def interactive_manual_check_historical_prices(instrument_code: str):
    """
    Do a daily update for futures contract prices, using IB historical data

    If any 'spikes' are found, run manual checks

    :return: Nothing
    """
    with dataBlob(log_name="Update-Historical-prices-manually") as data:
        diag_prices = diagPrices(data)
        list_of_codes_all = diag_prices.get_list_of_instruments_with_contract_prices()
        if instrument_code not in list_of_codes_all:
            print(
                "\n\n\ %s is not an instrument with price data \n\n" %
                instrument_code)
            raise Exception()
        update_historical_prices_with_checks_for_instrument(
            instrument_code, data, log=data.log.setup(
                instrument_code=instrument_code))

    return success


def update_historical_prices_with_checks_for_instrument(
        instrument_code, data, log):
    """
    Do a daily update for futures contract prices, using IB historical data

    Any 'spikes' are manually checked

    :param instrument_code: str
    :param data: dataBlob
    :param log: logger
    :return: None
    """
    diag_contracts = diagContracts(data)
    all_contracts_list = diag_contracts.get_all_contract_objects_for_instrument_code(
        instrument_code)
    contract_list = all_contracts_list.currently_sampling()

    if len(contract_list) == 0:
        log.warn("No contracts marked for sampling for %s" % instrument_code)
        return failure

    for contract_object in contract_list:
        update_historical_prices_with_checks_for_instrument_and_contract(
            contract_object, data, log=log.setup(contract_date=contract_object.date)
        )

    return success


def update_historical_prices_with_checks_for_instrument_and_contract(
    contract_object, data, log
):
    """
    Do a daily update for futures contract prices, using IB historical data, with checking

    :param contract_object: futuresContract
    :param data: data blob
    :param log: logger
    :return: None
    """
    diag_prices = diagPrices(data)
    intraday_frequency = diag_prices.get_intraday_frequency_for_historical_download()
    get_and_check_prices_for_frequency(
        data, log, contract_object, frequency=intraday_frequency
    )
    get_and_check_prices_for_frequency(
        data, log, contract_object, frequency="D")

    return success


def get_and_check_prices_for_frequency(
        data, log, contract_object, frequency="D"):

    broker_data = dataBroker(data)
    price_data = diagPrices(data)
    price_updater = updatePrices(data)

    try:
        old_prices = price_data.get_prices_for_contract_object(contract_object)
        ib_prices = broker_data.get_prices_at_frequency_for_contract_object(
            contract_object, frequency
        )
        if len(ib_prices) == 0:
            raise Exception(
                "No IB prices found for %s nothing to check" %
                str(contract_object))

        print(
            "\n\n Manually checking prices for %s \n\n" %
            str(contract_object))
        new_prices_checked = manual_price_checker(
            old_prices,
            ib_prices,
            column_to_check="FINAL",
            delta_columns=["OPEN", "HIGH", "LOW"],
            type_new_data=futuresContractPrices,
        )
        result = price_updater.update_prices_for_contract(
            contract_object, new_prices_checked, check_for_spike=False
        )
        return result

    except Exception as e:
        log.warn(
            "Exception %s when getting or checking data at frequency %s for %s"
            % (e, frequency, str(contract_object))
        )
        return failure
