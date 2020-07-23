"""
Simplest possible execution method, one market order
"""
from syscore.objects import missing_order
from sysproduction.data.broker import dataBroker

def algo_market(data, contract_order):
    """
    Simplest possible execution algo
    Submits a single market order for the entire quantity

    :param data: dataBlob
    :param contract_order: contractOrder

    :returns: tuple, (broker_order, reference of controlling algo)
    """
    log = contract_order.log_with_attributes(data.log)

    if not contract_order.fill_equals_zero():
        log.warn("Simple market algo can only deal with orders that have no existing fill, not %s!" % str(contract_order))
        return missing_order, ""

    data_broker = dataBroker(data)

    broker_order_with_controls = data_broker.get_and_submit_broker_order_for_contract_order(contract_order)
    broker_order = broker_order_with_controls.order

    # The algo remains in control until the fills are done, these are picked up elsewhere as this is a fire
    #    and forget algo
    reference_of_controlling_algo = "algo_market"

    return broker_order, reference_of_controlling_algo

