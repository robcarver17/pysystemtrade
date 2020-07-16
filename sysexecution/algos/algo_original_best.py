"""
This is the original 'best execution' algo I used in my legacy system
"""
from syscore.objects import missing_order, missing_data
from sysproduction.data.broker import dataBroker

PASSIVE_TIME_OUT = 300
TOTAL_TIME_OUT = 600
IMBALANCE_THRESHOLD = 5

def original_best(data, contract_order):
    """
    This is the original 'best execution' algo I used in my legacy system
    It's behaviour is described here
       https://qoppac.blogspot.com/2014/10/the-worlds-simplest-execution-algorithim.html

    :param data: dataBlob
    :param contract_order: contractOrder

    :returns: tuple, (broker_order, reference of controlling algo)
    """
    no_trade_possible = missing_order, None

    log = contract_order.log_with_attributes(data.log)
    data_broker = dataBroker(data)

    # We can deal with partially filled orders: that's how hard we are!
    remaining_contract_order = contract_order.order_with_remaining()

    ## check liquidity, and if neccessary carve up order
    ## Note for spread orders we check liquidity in the component markets
    qty = data_broker.get_largest_offside_liquid_size_for_contract_order_by_leg(remaining_contract_order)
    if qty.equals_zero():
        ## Nothing we can do here
        log.msg("Can't do any of size %s so not trading at all" % str(remaining_contract_order.trade))

        return no_trade_possible

    if qty!=remaining_contract_order.trade:
        log.msg("Cut down order to size %s from %s" % (str(qty), str(remaining_contract_order.trade)))

    ## get ticker
    ## create on tick object
    ticker_object = data_broker.get_ticker_object_for_order(remaining_contract_order)
    reference_tick = ticker_object.wait_for_valid_bid_and_ask_and_return_current_tick(wait_time_seconds=10)

    # Try and get limit price from ticker
    # We ignore the limit price given in the contract order: need to create a different order type for those
    tick_analysis = ticker_object.analyse_for_tick(reference_tick)

    if tick_analysis is missing_data:
        ## IF WE DO THIS HOW DO WE SET UP THE FIRST TICK?
        ## Get limit price from legs: we use the mid price because the net of offside prices is likely to be somewhat optimistic
        ## limit_price_from_legs = data_broker.get_net_mid_price_for_contract_order_by_leg(remaining_contract_order)

        #limit_price = limit_price_from_legs
        #if np.isnan(limit_price):
        log.warn("Can't get market data for %s so not trading with limit order %s" % (contract_order.instrument_code,
                                                                                      str(contract_order)))
        #return no_trade_possible

    else:
        limit_price = tick_analysis.offside_price

    # what if both empty
    order_type = "limit"


    ## create and issue limit order
    broker_order_with_controls = data_broker.get_and_submit_broker_order_for_contract_order_with_quantity(remaining_contract_order, qty,
                                                                                            order_type = order_type,
                                                                                            limit_price=limit_price)
    ticker_object.clear_and_add_reference_as_first_tick(reference_tick)

    broker_order_with_controls, ticker_object = manage_trade(data, broker_order_with_controls, ticker_object)

    ## on fill processing
    data_broker.cancel_market_data_for_order(remaining_contract_order)

    reference_of_controlling_algo = "original_best"

    # how do we deal with partial fills? Set the broker order trade size equal to the fill
    # then the rest is up for grabs
    # if nothing executed, return missing order
    broker_order = broker_order_with_controls.order

    return broker_order, reference_of_controlling_algo

def manage_trade(data, broker_order_with_controls, ticker_object):
    log = broker_order_with_controls.order.log_with_attributes(data.log)
    data_broker = dataBroker(data)

    trade_open = True
    aggressive = False
    while trade_open:
        if aggressive:
            new_limit_price = check_current_limit_price_at_inside_spread(broker_order_with_controls, ticker_object)
            if new_limit_price is not None:
                broker_order_with_controls = data_broker.modify_limit_price_given_control_object(broker_order_with_controls, new_limit_price)
                log.msg("Limit price has changed to %f" % new_limit_price)
        else:
            reason_to_switch = switch_to_aggressive(broker_order_with_controls, ticker_object)
            if reason_to_switch is not None:
                log.msg("Switch to aggressive because %s" % reason_to_switch)
                aggressive = True

        if broker_order_with_controls.completed():
            log.msg("Trade completed")
            break

        if broker_order_with_controls.seconds_since_submission() > TOTAL_TIME_OUT:
            ## what if market about to close....?
            log.msg("Run out of time: cancelling")
            data_broker.cancel_order_given_control_object(broker_order_with_controls)

            ## wait for cancel?
            # data_broker.check_order_is_cancelled_given_control_object
            break

    return broker_order_with_controls, ticker_object


def switch_to_aggressive(broker_order_with_controls, ticker_object):
    if broker_order_with_controls.seconds_since_submission() > PASSIVE_TIME_OUT:
        return "Time out after %f seconds" % broker_order_with_controls.seconds_since_submission()
    elif ticker_object.adverse_price_movement_vs_reference():
        return "Adverse price movement"
    elif ticker_object.latest_imbalance_ratio() > IMBALANCE_THRESHOLD:
        return "Imbalance ratio of %f exceeds threshold" %ticker_object.latest_imbalance_ratio()

    return None

def check_current_limit_price_at_inside_spread(broker_order_with_controls, ticker_object):
    current_limit_price = broker_order_with_controls.current_limit_price
    current_side_price = ticker_object.current_side_price

    if current_limit_price==current_side_price:
        return None

    ## change limit
    new_limit_price = current_side_price

    return new_limit_price