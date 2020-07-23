"""
Allocate which algo is doing a list of contract orders

Depends on instrument order and type of order

"""
from sysproduction.data.orders import dataOrders
from sysproduction.data.broker import dataBroker
from syscore.objects import missing_order

list_of_algos = ["sysexecution.algos.algo_market.algo_market", "sysexecution.algos.algo_original_best.original_best"]


def allocate_algo_to_list_of_contract_orders(data, instrument_order, list_of_contract_orders):
    """

    :param data: dataBlog
    :param instrument_order: parent instrument order
    :param list_of_contract_orders:
    :return: list of contract orders with algo added
    """

    new_list_of_contract_orders = []
    for contract_order in list_of_contract_orders:
        contract_order = check_and_if_required_allocate_algo_to_single_contract_order(data, contract_order)
        new_list_of_contract_orders.append(contract_order)

    return new_list_of_contract_orders

def check_and_if_required_allocate_algo_to_single_contract_order(data, contract_order):
    """

    :param data: dataBlog
    :param instrument_order: parent instrument order
    :param list_of_contract_orders:
    :return: list of contract orders with algo added
    """
    log = contract_order.log_with_attributes(data.log)

    if contract_order.algo_to_use!='':
        ## Already done
        return contract_order

    instrument_order_id = contract_order.parent
    order_data = dataOrders(data)

    instrument_stack = order_data.instrument_stack()
    instrument_order = instrument_stack.get_order_with_id_from_stack(instrument_order_id)
    if instrument_order is missing_order:
        log.warn("Couldn't find instrument order so allocating default algo_market")
        contract_order.algo_to_use = "sysexecution.algos.algo_market.algo_market"
        return contract_order
    else:
        instrument_order_type = instrument_order.order_type

        # not used yet, but maybe in the future
        is_roll_order = instrument_order.roll_order

    data_broker = dataBroker(data)
    short_of_time = data_broker.less_than_one_hour_of_trading_leg_for_instrument_code_and_contract_date(contract_order.instrument_code,
                                                                                        contract_order.contract_id[0])

    contract_order.algo_to_use = "sysexecution.algos.algo_market.algo_market"

    """
    UNCOMMENT WHEN BEST ALGO TESTED
    if instrument_order_type == 'market':
        log.msg("Market order type, so allocating to algo_market")
        contract_order.algo_to_use = "sysexecution.algos.algo_market.algo_market"
    elif instrument_order_type == "best":
        if short_of_time:
            log.warn("Short of time, so allocating to algo_market")
            contract_order.algo_to_use = "sysexecution.algos.algo_market.algo_market"
        else:
            log.msg("'Best' order so allocating to original_best")
            contract_order.algo_to_use = "sysexecution.algos.algo_original_best.original_best"
    else:
        log.warn("Don't recognise order type %s so allocating to default algo_market" % instrument_order_type)
        contract_order.algo_to_use = "sysexecution.algos.algo_market.algo_market"
    """

    return contract_order