from syscore.exceptions import missingData
from sysbrokers.IB.ib_futures_contract_price_data import (
    futuresContract,
)
from syscore.dateutils import DAILY_PRICE_FREQ, HOURLY_FREQ, Frequency
from sysdata.data_blob import dataBlob

from sysproduction.data.broker import dataBroker
from sysproduction.data.prices import updatePrices
from sysproduction.update_historical_prices import write_merged_prices_for_contract

def seed_price_data_from_IB(instrument_code):
    data = dataBlob()
    data_broker = dataBroker(data)

    list_of_contracts = data_broker.get_list_of_contract_dates_for_instrument_code(
        instrument_code, allow_expired=True
    )

    for contract_date in list_of_contracts:
        contract_object = futuresContract(instrument_code, contract_date)
        seed_price_data_for_contract(data=data, contract_object=contract_object)



def seed_price_data_for_contract(data: dataBlob, contract_object: futuresContract):
    list_of_frequencies= [DAILY_PRICE_FREQ, HOURLY_FREQ]
    for frequency in [DAILY_PRICE_FREQ, HOURLY_FREQ]:
        seed_price_data_for_contract_at_frequency(data=data, contract_object=contract_object, frequency=frequency)

    write_merged_prices_for_contract(
        data, contract_object=contract_object, list_of_frequencies=list_of_frequencies
    )


def seed_price_data_for_contract_at_frequency(data: dataBlob, contract_object: futuresContract, frequency: Frequency):

    data_broker = dataBroker(data)
    update_prices = updatePrices(data)

    ## We do this slightly tortorous thing because there are energy contracts
    ## which don't expire in the month they are labelled with
    ## So for example, CRUDE_W 202106 actually expires on 20210528

    date_str = contract_object.contract_date.date_str[:6]
    new_contract = futuresContract(contract_object.instrument, date_str)

    log = new_contract.specific_log(data.log)
    try:
        prices = data_broker.get_prices_at_frequency_for_potentially_expired_contract_object(
            new_contract,
            frequency=frequency
        )
    except missingData:
        log.warn("Error getting data for %s" % str(new_contract))
        return None

    if len(prices) == 0:
        log.warn("No price data for %s" % str(new_contract))
    else:
        update_prices.overwrite_prices_at_frequency_for_contract(contract_object=contract_object,
                                                                 frequency=frequency,
                                                                 new_prices=prices)


if __name__ == "__main__":
    print("Get initial price data from IB")
    instrument_code = input("Instrument code? <return to abort> ")
    if instrument_code == "":
        exit()

    seed_price_data_from_IB(instrument_code)
