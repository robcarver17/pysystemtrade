"""
This is the original 'best execution' algo I used in my legacy system
"""
from syscore.objects import missing_order, missing_data
from syscore.genutils import quickTimer
from sysproduction.data.broker import dataBroker

# Here are the algo parameters
# Hard coded; if you want to try different parameters make a hard copy and give it a different reference
PASSIVE_TIME_OUT = 300
TOTAL_TIME_OUT = 600
IMBALANCE_THRESHOLD = 5

SIZE_LIMIT = 1

def original_best(data, contract_order):
    """
    This is the original 'best execution' algo I used in my legacy system
    It's behaviour is described here
       https://qoppac.blogspot.com/2014/10/the-worlds-simplest-execution-algorithim.html

    :param data: dataBlob
    :param contract_order: contractOrder

    :returns: tuple, (broker_order, reference of controlling algo)
    """
    log = contract_order.log_with_attributes(data.log)
    data_broker = dataBroker(data)

    broker_order_with_controls, ticker_object = prepare_and_submit_trade(data, contract_order)
    if broker_order_with_controls is missing_order:
        no_trade_possible = missing_order, None
        return no_trade_possible

    broker_order_with_controls, ticker_object = manage_trade(data, broker_order_with_controls, ticker_object)

    data_broker.cancel_market_data_for_order(broker_order_with_controls.order)

    ## update the order one more time
    broker_order_with_controls.update_order()
    broker_order = broker_order_with_controls.order

    ## This order will now contain all fills so we set trades==fills so the order is treated as completed
    broker_order.set_trade_to_fill()

    # not fire and forget so allowed to
    reference_of_controlling_algo = None

    return broker_order, reference_of_controlling_algo

def prepare_and_submit_trade(data, contract_order):
    log = contract_order.log_with_attributes(data.log)
    data_broker = dataBroker(data)

    cut_down_contract_order = contract_order.order_with_min_size(SIZE_LIMIT)
    if cut_down_contract_order.trade!=contract_order.trade:
        log.msg("Cut down order to size %s from %s because of algo size limit" %
                (str(contract_order.trade), str(cut_down_contract_order.trade)))

    ## check liquidity, and if neccessary carve up order
    ## Note for spread orders we check liquidity in the component markets
    qty = data_broker.get_largest_offside_liquid_size_for_contract_order_by_leg(cut_down_contract_order)
    if qty.equals_zero():
        ## Nothing we can do here
        log.msg("Can't do any of size %s so not trading at all" % str(cut_down_contract_order.trade))

        return missing_order

    if qty!=contract_order.trade:
        log.msg("Cut down order to size %s from %s because of liquidity" % (str(qty), str(cut_down_contract_order.trade)))

    liquidity_sized_contract_order = cut_down_contract_order.replace_trade_only_use_for_unsubmitted_trades(qty)

    ## get ticker
    ## create on tick object
    ticker_object = data_broker.get_ticker_object_for_order(liquidity_sized_contract_order)
    reference_tick = ticker_object.wait_for_valid_bid_and_ask_and_return_current_tick(wait_time_seconds=10)

    # Try and get limit price from ticker
    # We ignore the limit price given in the contract order: need to create a different order type for those
    tick_analysis = ticker_object.analyse_for_tick(reference_tick)

    if tick_analysis is missing_data:
        """
        Here's a possible solution for markets with no active spread orders, but it has potential problems
        Probably better to do these as market orders
        
        ## Get limit price from legs: we use the mid price because the net of offside prices is likely to be somewhat optimistic
        ## limit_price_from_legs = data_broker.get_net_mid_price_for_contract_order_by_leg(remaining_contract_order)

        #limit_price = limit_price_from_legs
        
        """
        log.warn("Can't get market data for %s so not trading with limit order %s" % (contract_order.instrument_code,
                                                                                      str(contract_order)))
        return missing_order

    else:
        limit_price = tick_analysis.offside_price

    # what if both empty...
    order_type = "limit"

    ## create and issue limit order
    broker_order_with_controls = data_broker.\
        get_and_submit_broker_order_for_contract_order(cut_down_contract_order, order_type = order_type,
                                                                                            limit_price=limit_price)

    ticker_object.clear_and_add_reference_as_first_tick(reference_tick)

    return ticker_object, broker_order_with_controls

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
            ## Need some way of switching to market order if market about to close...

            log.msg("Run out of time: cancelling")
            broker_order_with_controls = cancel_order(data, broker_order_with_controls)
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

def cancel_order(data, broker_order_with_controls):
    log = broker_order_with_controls.order.log_with_attributes(data.log)
    data_broker = data
    data_broker.cancel_order_given_control_object(broker_order_with_controls)

    # Wait for cancel. It's vitual we do this since if a fill comes in before we finish it will screw
    #   everyting up...
    timer = quickTimer(seconds = 600)
    not_cancelled = True
    while not_cancelled:
        is_cancelled = data_broker.check_order_is_cancelled_given_control_object(broker_order_with_controls)
        if is_cancelled:
            log.msg("Cancelled order")
            break
        if timer.finished():
            log.critical("Ran out of time to cancel order - may cause weird behaviour!")
            break


    return broker_order_with_controls

