from syscore.exceptions import missingData
from sysbrokers.IB.ib_futures_contract_price_data import (
    futuresContract,
)
from syscore.dateutils import DAILY_PRICE_FREQ, HOURLY_FREQ, Frequency
from sysproduction.data.broker import dataBroker
from sysproduction.data.prices import updatePrices
from sysinit.futures.create_hourly_and_daily import write_split_data_for_instrument


def seed_price_data_from_IB(instrument_code):
    data_broker = dataBroker()

    list_of_contracts = data_broker.get_list_of_contract_dates_for_instrument_code(
        instrument_code, allow_expired=True
    )

    for contract in list_of_contracts:
        seed_price_data_for_contract(contract)

    write_split_data_for_instrument(instrument_code)


def seed_price_data_for_contract( contract: futuresContract):
    ## We do this slightly tortorous thing because there are energy contracts
    ## which don't expire in the month they are labelled with
    ## So for example, CRUDE_W 202106 actually expires on 20210528
    for frequency in [DAILY_PRICE_FREQ, HOURLY_FREQ]:
        seed_price_data_for_contract_at_frequency(contract, frequency=frequency)

def seed_price_data_for_contract_at_frequency( contract: futuresContract, frequency: Frequency):
    ## We do this slightly tortorous thing because there are energy contracts
    ## which don't expire in the month they are labelled with
    ## So for example, CRUDE_W 202106 actually expires on 20210528

    data_broker = dataBroker()
    update_prices = updatePrices()

    date_str = contract.contract_date.date_str[:6]
    new_contract = futuresContract(contract.instrument, date_str)
    try:
        prices = data_broker.get_prices_at_frequency_for_potentially_expired_contract_object(
            new_contract,
            frequency=frequency
        )
    except missingData:
        prices = []

    if len(prices) == 0:
        print("No data!")
    else:
        update_prices.overwrite_prices_at_frequency_for_contract(contract_object=contract,
                                                                 frequency=frequency,
                                                                 new_prices=prices)


if __name__ == "__main__":
    print("Get initial price data from IB")
    instrument_code = input("Instrument code? <return to abort> ")
    if instrument_code == "":
        exit()

    seed_price_data_from_IB(instrument_code)
