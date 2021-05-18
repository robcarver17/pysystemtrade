
from sysdata.data_blob import dataBlob
from sysbrokers.IB.ib_futures_contract_price_data import ibFuturesContractPriceData

def seed_price_data_from_IB(instrument_code):
data = dataBlob()
data.add_class_list([ibFuturesContractPriceData])
data.\
    broker_futures_contract_price.\
    contracts_with_price_data_for_instrument_code(instrument_code, include_expired=True)

if __name__ == "__main__":
    print("Get initial price data from IB")
    instrument_code = input("Instrument code? <return to abort")
    if instrument_code == "":
        exit()

    seed_price_data_from_IB(instrument_code)