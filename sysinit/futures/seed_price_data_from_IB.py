from sysdata.data_blob import dataBlob
from sysbrokers.IB.ib_futures_contract_price_data import ibFuturesContractPriceData, futuresContract
from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData

def seed_price_data_from_IB(instrument_code):
    data = dataBlob()
    data.add_class_list([ibFuturesContractPriceData, arcticFuturesContractPriceData])
    list_of_contracts = data.\
        broker_futures_contract_price.\
        contracts_with_price_data_for_instrument_code(instrument_code,allow_expired=True)

    for contract in list_of_contracts:
        seed_price_data_for_contract(data, contract)

def seed_price_data_for_contract(data: dataBlob, contract: futuresContract):
    prices = data.\
        broker_futures_contract_price. \
        get_prices_at_frequency_for_potentially_expired_contract_object(contract)
    if len(prices)==0:
        print("No data!")

    ## Use update to avoid issues with overwriting
    data.db_futures_contract_price.update_prices_for_contract(contract, prices)


if __name__ == "__main__":
    print("Get initial price data from IB")
    instrument_code = input("Instrument code? <return to abort")
    if instrument_code == "":
        exit()

    seed_price_data_from_IB(instrument_code)