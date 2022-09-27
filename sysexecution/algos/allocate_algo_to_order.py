"""
Allocate which algo is doing a list of contract orders

Depends on instrument order and type of order

"""
from sysproduction.data.orders import dataOrders
from sysproduction.data.broker import dataBroker
from syscore.objects import missing_order, arg_not_supplied
from sysdata.data_blob import dataBlob
from sysexecution.orders.instrument_orders import (
    instrumentOrder,
    zero_roll_order_type,
    balance_order_type,
    best_order_type,
    limit_order_type,
    market_order_type,
)
from sysexecution.orders.contract_orders import contractOrder
from sysexecution.orders.list_of_orders import listOfOrders

DEFAULT_ALGO = MARKET_ALGO = "sysexecution.algos.algo_market.algoMarket"
ORIGINAL_BEST = "sysexecution.algos.algo_original_best.algoOriginalBest"
LIMIT_ALGO = "sysexecution.algos.algo_limit_orders.algoLimit"

# Don't trade with an algo in last 30 minutes
HOURS_BEFORE_MARKET_CLOSE_TO_SWITCH_TO_MARKET = 0.5

list_of_algos = [MARKET_ALGO, ORIGINAL_BEST]


def allocate_algo_to_list_of_contract_orders(
    data: dataBlob,
    list_of_contract_orders: listOfOrders,
    instrument_order: instrumentOrder,
) -> listOfOrders:
    """

    :param data: dataBlog
    :param instrument_order: parent instrument order
    :param list_of_contract_orders:
    :return: list of contract orders with algo added
    """

    new_list_of_contract_orders = []
    for contract_order in list_of_contract_orders:
        contract_order = check_and_if_required_allocate_algo_to_single_contract_order(
            data, contract_order, instrument_order
        )
        new_list_of_contract_orders.append(contract_order)

    new_list_of_contract_orders = listOfOrders(new_list_of_contract_orders)

    return new_list_of_contract_orders


def check_and_if_required_allocate_algo_to_single_contract_order(
    data: dataBlob, contract_order: contractOrder, instrument_order: instrumentOrder
) -> contractOrder:
    """

    :param data: dataBlog
    :param instrument_order: parent instrument order
    :param list_of_contract_orders:
    :return: list of contract orders with algo added
    """
    log = contract_order.log_with_attributes(data.log)

    if contract_order.algo_to_use != "":
        # Already done
        return contract_order

    instrument_order_type = instrument_order.order_type

    # not used yet, but maybe in the future
    is_roll_order = instrument_order.roll_order

    if instrument_order_type == market_order_type:
        log.msg("Market order type, so allocating to algo_market")
        contract_order.algo_to_use = MARKET_ALGO

    elif (
        instrument_order_type == best_order_type
        or instrument_order_type == zero_roll_order_type
    ):
        contract_order = allocate_for_best_execution_no_limit(
            data=data, contract_order=contract_order
        )

    elif instrument_order_type == limit_order_type:
        contract_order = allocate_for_limit_order(
            data, contract_order=contract_order
        )

    elif instrument_order_type == balance_order_type:
        log.critical("Balance orders aren't executed, shouldn't even be here!")
        return missing_order
    else:
        log.warn(
            "Don't recognise order type %s so allocating to default algo_market"
            % instrument_order_type
        )
        contract_order.algo_to_use = DEFAULT_ALGO

    return contract_order


def allocate_for_best_execution_no_limit(
    data: dataBlob, contract_order: contractOrder
) -> contractOrder:
    # in the future could be randomized...
    log = contract_order.log_with_attributes(data.log)
    data_broker = dataBroker(data)
    short_of_time = data_broker.less_than_N_hours_of_trading_left_for_contract(
        contract_order.futures_contract,
        N_hours=HOURS_BEFORE_MARKET_CLOSE_TO_SWITCH_TO_MARKET,
    )

    if short_of_time:
        log.warn("Short of time, so allocating to algo_market")
        contract_order.algo_to_use = MARKET_ALGO
    else:
        log.msg("'Best' order so allocating to original_best")
        contract_order.algo_to_use = ORIGINAL_BEST

    return contract_order

def allocate_for_limit_order(
    data: dataBlob, contract_order: contractOrder
) -> contractOrder:
    # in the future could be randomized...
    log = contract_order.log_with_attributes(data.log)
    log.msg("Allocating to limit order")
    contract_order.algo_to_use = LIMIT_ALGO

    return contract_order
