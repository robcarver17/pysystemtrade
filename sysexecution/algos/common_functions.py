# functions used by multiple algos

from syscore.exceptions import orderCannotBeModified
from sysdata.data_blob import dataBlob
from sysproduction.data.broker import dataBroker
from syscore.genutils import quickTimer
from sysexecution.order_stacks.broker_order_stack import orderWithControls

# how often do algos talk
MESSAGING_FREQUENCY = 30

# how long to cancel an order
CANCEL_WAIT_TIME = 60


def post_trade_processing(
    data: dataBlob, broker_order_with_controls: orderWithControls
) -> orderWithControls:
    data_broker = dataBroker(data)
    data_broker.cancel_market_data_for_order(broker_order_with_controls.order)

    # update the order one more time
    broker_order_with_controls.update_order()

    # This order will now contain all fills so we set trades==fills
    # so the order is treated as completed
    # FIXME don't think I need to do this
    # broker_order_with_controls.order.change_trade_qty_to_filled_qty()

    return broker_order_with_controls


def cancel_order(
    data: dataBlob, broker_order_with_controls: orderWithControls
) -> orderWithControls:

    log = broker_order_with_controls.order.log_with_attributes(data.log)
    data_broker = dataBroker(data)
    data_broker.cancel_order_given_control_object(broker_order_with_controls)

    # Wait for cancel. It's vitual we do this since if a fill comes in before we finish it will screw
    #   everything up...
    timer = quickTimer(seconds=CANCEL_WAIT_TIME)
    not_cancelled = True
    while not_cancelled:
        is_cancelled = data_broker.check_order_is_cancelled_given_control_object(
            broker_order_with_controls
        )
        if is_cancelled:
            log.msg("Cancelled order")
            break
        if timer.finished:
            log.warn("Ran out of time to cancel order - may cause weird behaviour!")
            break

    return broker_order_with_controls


def set_limit_price(
    data: dataBlob,
    broker_order_with_controls: orderWithControls,
    new_limit_price: float,
):

    log = broker_order_with_controls.order.log_with_attributes(data.log)
    data_broker = dataBroker(data)

    try:
        broker_order_with_controls = (
            data_broker.modify_limit_price_given_control_object(
                broker_order_with_controls, new_limit_price
            )
        )
        log.msg("Tried to change limit price to %f" % new_limit_price)
    except orderCannotBeModified as error:
        log.msg("Can't modify limit price for order, error %s" % str(error))

    return broker_order_with_controls


limit_price_is_at_inside_spread = -99999999999999.99


def check_current_limit_price_at_inside_spread(
    broker_order_with_controls: orderWithControls,
) -> float:
    # When we are aggressive we want to remain on the correct side of the
    # spread

    ## We store two types of limit price. The limit price saved in the broker order (current_limit_price),
    ##   and the limit price in the IB control object (broker_limit_price)
    ## The former is changed when we change a limit price, the latter is not, we wait for IB to
    ##    update it and reflect the object
    current_limit_price = broker_order_with_controls.broker_limit_price()

    ticker_object = broker_order_with_controls.ticker
    current_side_price = ticker_object.current_side_price

    if current_limit_price == current_side_price:
        return limit_price_is_at_inside_spread

    # change limit
    new_limit_price = current_side_price

    return new_limit_price


def file_log_report_market_order(log, broker_order_with_controls: orderWithControls):

    ticker_object = broker_order_with_controls.ticker
    current_tick = str(ticker_object.current_tick())

    log_report = "Market order execution current tick %s" % current_tick

    log.msg(log_report)
