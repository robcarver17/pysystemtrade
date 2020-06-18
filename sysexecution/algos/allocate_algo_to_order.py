"""
Allocate which algo is doing a list of contract orders

Depends on instrument order and type of order

For now one algo only: market order

In the future will use algos, and possibly even multiple algos randomly decided or tuned for instrument
"""
from sysproduction.data.orders import dataOrders
from syscore.objects import missing_order

def allocate_algo_to_list_of_contract_orders(data, instrument_order, list_of_contract_orders):
    """

    :param data: dataBlog
    :param instrument_order: parent instrument order
    :param list_of_contract_orders:
    :return: list of contract orders with algo added
    """

    # not used yet, but maybe in the future
    instrument_order_type = instrument_order.order_type
    is_roll_order = instrument_order.roll_order

    for contract_order in list_of_contract_orders:
        contract_order.algo_to_use = "sysexecution.algos.algo_market.algo_market"

    return list_of_contract_orders

def check_and_if_required_allocate_algo_to_single_contract_order(data, contract_order):
    """

    :param data: dataBlog
    :param instrument_order: parent instrument order
    :param list_of_contract_orders:
    :return: list of contract orders with algo added
    """

    if contract_order.algo_to_use!='':
        ## Already done
        return contract_order


    instrument_order_id = contract_order.parent
    order_data = dataOrders(data)

    instrument_stack = order_data.instrument_stack()
    instrument_order = instrument_stack.get_order_with_id_from_stack(instrument_order_id)
    if instrument_order is missing_order:
        ## Have to use some kind of default order, but for now the logic isn't required since we
        ##   only have market orders.
        pass
    else:
        # not used yet, but maybe in the future
        instrument_order_type = instrument_order.order_type
        is_roll_order = instrument_order.roll_order

    contract_order.algo_to_use = "sysexecution.algos.algo_market.algo_market"

    return contract_order