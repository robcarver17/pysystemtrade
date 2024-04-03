from sysbrokers.IB.ib_capital_data import ibCapitalData
from sysbrokers.IB.ib_Fx_prices_data import ibFxPricesData
from sysbrokers.IB.ib_futures_contract_price_data import ibFuturesContractPriceData
from sysbrokers.IB.ib_futures_contracts_data import ibFuturesContractData
from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData
from sysbrokers.IB.ib_contract_position_data import ibContractPositionData
from sysbrokers.IB.ib_orders import ibExecutionStackData
from sysbrokers.IB.ib_static_data import ibStaticData
from sysbrokers.IB.ib_fx_handling import ibFxHandlingData
from sysbrokers.IB.ib_broker_commissions import ibFuturesContractCommissionData

from syscore.objects import resolve_function
from sysdata.data_blob import dataBlob


def get_broker_class_list(data: dataBlob):
    """
    Returns a list of classes that are specific to the broker being used.
    IB classes are returned by default. If you would like to use a different
    broker, then create a custom get_class_list() function in your private
    directory and specify the function name in private_config.yaml under the
    field name: broker_factory_func
    """
    config = data.config

    broker_factory_func = config.get_element_or_default(
        "broker_factory_func", get_ib_class_list
    )

    get_class_list = resolve_function(broker_factory_func)

    broker_class_list = get_class_list()

    return broker_class_list


def get_ib_class_list():
    return [
        ibFxPricesData,
        ibFuturesContractPriceData,
        ibFuturesContractData,
        ibContractPositionData,
        ibExecutionStackData,
        ibStaticData,
        ibCapitalData,
        ibFuturesInstrumentData,
        ibFxHandlingData,
        ibFuturesContractCommissionData
    ]
