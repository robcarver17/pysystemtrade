"""
Update historical data per contract from interactive brokers data, dump into mongodb
"""

from syscore.objects import success, failure
from syscore.merge_data import spike_in_data

from syscore.dateutils import DAILY_PRICE_FREQ, Frequency

from sysobjects.contracts import futuresContract

from sysdata.data_blob import dataBlob
from sysproduction.data.prices import diagPrices, updatePrices
from sysproduction.data.broker import dataBroker
from sysproduction.data.contracts import dataContracts
from syslogdiag.email_via_db_interface import send_production_mail_msg


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
        update_historical_prices_with_data(data)

def update_historical_prices_with_data(data: dataBlob):
    price_data = diagPrices(data)
    list_of_codes_all = price_data.get_list_of_instruments_in_multiple_prices()
    for instrument_code in list_of_codes_all:
        data.log.label(instrument_code = instrument_code)
        update_historical_prices_for_instrument(
            instrument_code, data)


def update_historical_prices_for_instrument(instrument_code: str, data: dataBlob):
    """
    Do a daily update for futures contract prices, using IB historical data

    :param instrument_code: str
    :param data: dataBlob
    :return: None
    """
    diag_contracts = dataContracts(data)
    all_contracts_list = diag_contracts.get_all_contract_objects_for_instrument_code(
        instrument_code)
    contract_list = all_contracts_list.currently_sampling()

    if len(contract_list) == 0:
        data.log.warn("No contracts marked for sampling for %s" % instrument_code)
        return failure

    for contract_object in contract_list:
        data.log.label(contract_date = contract_object.date_str)
        update_historical_prices_for_instrument_and_contract(
            contract_object, data)

    return success


def update_historical_prices_for_instrument_and_contract(
        contract_object: futuresContract, data: dataBlob):
    """
    Do a daily update for futures contract prices, using IB historical data

    There are two different calls, the first using intraday frequency, the second daily.
    So in a typical session we'd get the hourly intraday prices for a given instrument,
    and then if that instrument has closed we'd also get a new end of day price.
    The end of day prices are given the artifical datetime stamp of 23:00:00
    (because I never collect data round that time).

    If the intraday call fails, we don't want to get daily data.
    Otherwise we wouldn't be able to subsequently backfill hourly prices that occured
    before the daily close being added (the code doesn't allow you to add prices that have
    a timestamp which is before the last timestamp in the existing data).

    That's why the result of the first call matters, and is used to abort the function prematurely before we get to daily data.
    We don't care about the second call succeeding or failing, and so the result of that is ignored.

    :param contract_object: futuresContract
    :param data: data blob
    :return: None
    """
    diag_prices = diagPrices(data)
    intraday_frequency = diag_prices.get_intraday_frequency_for_historical_download()
    daily_frequency = DAILY_PRICE_FREQ

    # Get *intraday* data (defaults to hourly)
    result = get_and_add_prices_for_frequency(
        data, contract_object, frequency=intraday_frequency
    )
    if result is failure:
        # Skip daily data if intraday not working

        return None

    # Get daily data
    # we don't care about the result flag for this
    get_and_add_prices_for_frequency(
        data, contract_object, frequency=daily_frequency)


def get_and_add_prices_for_frequency(
        data: dataBlob, contract_object: futuresContract, frequency: Frequency = DAILY_PRICE_FREQ):
    broker_data_source = dataBroker(data)
    db_futures_prices = updatePrices(data)

    broker_prices = broker_data_source.get_prices_at_frequency_for_contract_object(
        contract_object, frequency)

    if len(broker_prices)==0:
        data.log.msg("No prices from broker for %s" % str(contract_object))
        return failure

    error_or_rows_added = db_futures_prices.update_prices_for_contract(
        contract_object, broker_prices, check_for_spike=True
    )

    if error_or_rows_added is spike_in_data:
        report_price_spike(data, contract_object)
        return failure

    data.log.msg(
        "Added %d rows at frequency %s for %s"
        % (error_or_rows_added, frequency, str(contract_object))
    )
    return success

def report_price_spike(data: dataBlob, contract_object: futuresContract):
    # SPIKE
    # Need to email user about this as will need manually checking
    msg = (
            "Spike found in prices for %s: need to manually check by running interactive_manual_check_historical_prices" %
            str(contract_object))
    data.log.warn(msg)
    try:
        send_production_mail_msg(
            data, msg, "Price Spike %s" %
                       contract_object.instrument_code)
    except BaseException:
        data.log.warn(
            "Couldn't send email about price spike for %s"
            % str(contract_object)
        )

