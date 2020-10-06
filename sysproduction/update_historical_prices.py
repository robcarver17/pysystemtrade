"""
Update historical data per contract from interactive brokers data, dump into mongodb
"""

from syscore.objects import success, failure, data_error

from sysproduction.data.get_data import dataBlob
from sysproduction.data.prices import diagPrices, updatePrices
from sysproduction.data.broker import dataBroker
from sysproduction.data.contracts import diagContracts
from sysproduction.diagnostic.emailing import send_production_mail_msg


def update_historical_prices():
    """
    Do a daily update for futures contract prices, using IB historical data

    :return: Nothing
    """
    with dataBlob(log_name="Update-Historical-Prices") as data:
        update_historical_price_object = updateHistoricalPrices(data)
        update_historical_price_object.update_historical_prices()
    return success


class updateHistoricalPrices(object):
    def __init__(self, data):
        self.data = data

    def update_historical_prices(self):
        data = self.data
        price_data = diagPrices(data)
        log = data.log
        list_of_codes_all = price_data.get_list_of_instruments_in_multiple_prices()
        for instrument_code in list_of_codes_all:
            update_historical_prices_for_instrument(
                instrument_code, data, log=log.setup(
                    instrument_code=instrument_code))


def update_historical_prices_for_instrument(instrument_code, data, log):
    """
    Do a daily update for futures contract prices, using IB historical data

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
        update_historical_prices_for_instrument_and_contract(
            contract_object, data, log=log.setup(
                contract_date=contract_object.date))

    return success


def update_historical_prices_for_instrument_and_contract(
        contract_object, data, log):
    """
    Do a daily update for futures contract prices, using IB historical data

    :param contract_object: futuresContract
    :param data: data blob
    :param log: logger
    :return: None
    """
    diag_prices = diagPrices(data)
    intraday_frequency = diag_prices.get_intraday_frequency_for_historical_download()
    result = get_and_add_prices_for_frequency(
        data, log, contract_object, frequency=intraday_frequency
    )
    if result is failure:
        # Skip daily data if intraday not working
        return failure

    result = get_and_add_prices_for_frequency(
        data, log, contract_object, frequency="D")

    return result


def get_and_add_prices_for_frequency(
        data, log, contract_object, frequency="D"):
    broker_data_source = dataBroker(data)
    db_futures_prices = updatePrices(data)

    try:
        ib_prices = broker_data_source.get_prices_at_frequency_for_contract_object(
            contract_object, frequency)
        rows_added = db_futures_prices.update_prices_for_contract(
            contract_object, ib_prices, check_for_spike=True
        )
        if rows_added is data_error:
            # SPIKE
            # Need to email user about this as will need manually checking
            msg = (
                "Spike found in prices for %s: need to manually check by running interactive_manual_check_historical_prices" %
                str(contract_object))
            log.warn(msg)
            try:
                send_production_mail_msg(
                    data, msg, "Price Spike %s" %
                    contract_object.instrument_code)
            except BaseException:
                log.warn(
                    "Couldn't send email about price spike for %s"
                    % str(contract_object)
                )

            return failure

        log.msg(
            "Added %d rows at frequency %s for %s"
            % (rows_added, frequency, str(contract_object))
        )
        return success

    except Exception as e:
        log.warn(
            "Exception %s when getting data at frequency %s for %s"
            % (e, frequency, str(contract_object))
        )
        return failure
