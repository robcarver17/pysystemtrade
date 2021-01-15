from syscore.objects import arg_not_supplied
from sysdata.data_blob import dataBlob
from sysproduction.data.broker import dataBroker
from sysproduction.data.contracts import diagContracts
from sysproduction.data.prices import diagPrices

from sysobjects.contracts import futuresContract


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

    contract = futuresContract(instrument_code, contract_id)

    data_broker = dataBroker(data)
    trading_hours = data_broker.get_trading_hours_for_contract(contract)

    return trading_hours
