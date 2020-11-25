from syscore.objects import arg_not_supplied
from sysdata.data_blob import dataBlob
from sysproduction.data.broker import dataBroker
from sysproduction.data.contracts import diagContracts
from sysproduction.data.prices import diagPrices

## MOVE SOME CODE FROM OUT OF IB CONTRACTS WHICH IS QUITE GENERIC

def print_trading_hours_for_all_instruments(data=arg_not_supplied):
    all_trading_hours = get_trading_hours_for_all_instruments(data)
    for key, value in sorted(all_trading_hours.items(), key=lambda x: x[0]):
        print("{} : {}".format(key, value))


def get_trading_hours_for_all_instruments(data=arg_not_supplied):
    if data is arg_not_supplied:
        data = dataBlob()

    diag_prices = diagPrices()
    list_of_instruments = diag_prices.get_list_of_instruments_with_contract_prices()

    all_trading_hours = {}
    for instrument_code in list_of_instruments:
        trading_hours = get_trading_hours_for_instrument(data, instrument_code)
        all_trading_hours[instrument_code] = trading_hours[:1]

    return all_trading_hours


def get_trading_hours_for_instrument(data, instrument_code):

    diag_contracts = diagContracts(data)
    contract_id = diag_contracts.get_priced_contract_id(instrument_code)

    data_broker = dataBroker(data)
    trading_hours = data_broker.get_trading_hours_for_instrument_code_and_contract_date(
        instrument_code, contract_id)

    return trading_hours
