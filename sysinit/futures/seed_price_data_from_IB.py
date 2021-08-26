from sysdata.data_blob import dataBlob
from sysbrokers.IB.ib_futures_contract_price_data import ibFuturesContractPriceData, futuresContract
from sysbrokers.IB.ib_futures_contracts_data import ibFuturesContractData
from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData

def seed_price_data_from_IB(instrument_code):
    data = dataBlob()
    data.add_class_list([ibFuturesContractPriceData, arcticFuturesContractPriceData,
                         ibFuturesContractData])
    list_of_contracts = data.\
        broker_futures_contract_price.\
        contracts_with_price_data_for_instrument_code(instrument_code,allow_expired=True)

    for contract in list_of_contracts:
        seed_price_data_for_contract(data, contract)

def seed_price_data_for_contract(data: dataBlob, contract: futuresContract):
    ## We do this slightly tortorous thing because there are energy contracts
    ## which don't expire in the month they are labelled with
    ## So for example, CRUDE_W 202106 actually expires on 20210528

    date_str = contract.contract_date.date_str[:6]
    new_contract = futuresContract(contract.instrument,
                                   date_str)
    prices = data.\
        broker_futures_contract_price. \
        get_prices_at_frequency_for_potentially_expired_contract_object(new_contract)
    if len(prices)==0:
        print("No data!")

    ## If you want to modify this script so it updates existing prices
    ## eg from barchart, then uncomment the following line and comment the next
    #data.db_futures_contract_price.update_prices_for_contract(contract, prices)
    data.db_futures_contract_price.write_prices_for_contract_object(new_contract, prices, ignore_duplication=True)

if __name__ == "__main__":
    print("Get initial price data from IB")
    instrument_code = input("Instrument code? <return to abort> ")
    if instrument_code == "":
        exit()

    seed_price_data_from_IB(instrument_code)