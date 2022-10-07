from sysobjects.contracts import futuresContract
from sysproduction.data.broker import dataBroker
from syscore.dateutils import DAILY_PRICE_FREQ


if __name__ == "__main__":
    print("Instrument must be set up in IB config, but doesn't have to appear anywhere else")
    print("Allows you to check the price and other details of a given instrument")

    instrument_code = input("Instrument code?")
    data_broker = dataBroker()
    meta_data = data_broker.get_brokers_instrument_with_metadata(instrument_code)

    print("Configured as %s" % str(meta_data))
    list_of_contract_dates = data_broker.get_list_of_contract_dates_for_instrument_code(instrument_code)
    list_of_contract_dates.sort()

    ## list months for roll config data
    print("Months with prices %s" % str(list_of_contract_dates))

    arbitrary_contract_date = list_of_contract_dates[0]
    ## prices
    contract_object = futuresContract(instrument_code, arbitrary_contract_date)
    ## price multipliers
    price_multiplier_from_ib = data_broker.broker_futures_contract_data.get_price_magnifier_for_contract(contract_object)
    print("Price multiplier from IB %s" % str(price_multiplier_from_ib))

    prices = data_broker.get_prices_at_frequency_for_contract_object(contract_object, DAILY_PRICE_FREQ)
    print("Prices for %s:" % str(contract_object))
    print(prices)