"""
Simplest possible execution method, one market order
"""
from syscore.objects import missing_order
from sysexecution.contract_orders import log_attributes_from_contract_order
from sysproduction.data.broker import dataBroker

def algo_market(data, contract_order):
    """
    Simplest possible execution algo
    Submits a single market order for the entire quantity

    :param data: dataBlob
    :param contract_order: contractOrder

    :returns: tuple, (broker_order, reference of controlling algo)
    """
    log = log_attributes_from_contract_order(data.log, contract_order)

    if not contract_order.fill_equals_zero():
        log.warn("Simple market algo can only deal with orders that have no existing fill, not %s!" % str(contract_order))
        return missing_order, ""

    qty = contract_order.trade

    if len(qty)>1:
        log.warn("Simple market algo can't yet deal with spread order' %s!" % str(
            contract_order))
        return missing_order, ""

    ## do full order
    qty_for_broker = qty

    data_broker = dataBroker(data)

    broker_order = data_broker.get_and_submit_broker_order_for_contract_order_as_market_order_with_quantity(contract_order, qty_for_broker)

    ## Need some kind of keystore for controlling Algos
    ## However as this is a 'fire and forget' algo that just runs once without any permanent thread
    ##   this doesn't matter, except perhaps for some complex case that we don't want to worry about right now
    ## When we introduce hooks for picking up fills, we're probably going to want to do this properly

    reference_of_controlling_algo = "algo_market"

    return broker_order, reference_of_controlling_algo

