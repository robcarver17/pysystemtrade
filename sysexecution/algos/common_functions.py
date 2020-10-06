# functions used by multiple algos

from sysproduction.data.broker import dataBroker
from syscore.genutils import quickTimer

# how often do algos talk
MESSAGING_FREQUENCY = 30

# how long to cancel an order
CANCEL_WAIT_TIME = 60


def post_trade_processing(data, broker_order_with_controls):
    data_broker = dataBroker(data)
    data_broker.cancel_market_data_for_order(broker_order_with_controls.order)

    # update the order one more time
    broker_order_with_controls.update_order()

    # This order will now hopefully contain all fills so we set trades==fills
    # so the order is treated as completed
    broker_order_with_controls.order.set_trade_to_fill()

    return broker_order_with_controls


def cancel_order(data, broker_order_with_controls):
    log = broker_order_with_controls.order.log_with_attributes(data.log)
    data_broker = dataBroker(data)
    data_broker.cancel_order_given_control_object(broker_order_with_controls)

    # Wait for cancel. It's vitual we do this since if a fill comes in before we finish it will screw
    #   everyting up...
    timer = quickTimer(seconds=CANCEL_WAIT_TIME)
    not_cancelled = True
    while not_cancelled:
        is_cancelled = data_broker.check_order_is_cancelled_given_control_object(
            broker_order_with_controls)
        if is_cancelled:
            log.msg("Cancelled order")
            break
        if timer.finished:
            log.warn("Ran out of time to cancel order - may cause weird behaviour!")
            break

    return broker_order_with_controls


def set_limit_price(data, broker_order_with_controls, new_limit_price):
    log = broker_order_with_controls.order.log_with_attributes(data.log)
    data_broker = dataBroker(data)
    can_be_modified = data_broker.check_order_can_be_modified_given_control_object(
        broker_order_with_controls)
    if can_be_modified:
        broker_order_with_controls = (
            data_broker.modify_limit_price_given_control_object(
                broker_order_with_controls, new_limit_price
            )
        )
        log.msg("Tried to change limit price to %f" % new_limit_price)
    else:
        log.msg("Can't modify limit price for order right now as status isn't good")

    return broker_order_with_controls


def check_current_limit_price_at_inside_spread(broker_order_with_controls):
    # When we are aggressive we want to remain on the correct side of the
    # spread

    correct_limit_price_on_order = (
        broker_order_with_controls.check_limit_price_consistent()
    )
    if correct_limit_price_on_order:
        current_limit_price = broker_order_with_controls.current_limit_price
    else:
        current_limit_price = broker_order_with_controls.broker_limit_price()

    ticker_object = broker_order_with_controls.ticker
    current_side_price = ticker_object.current_side_price

    if current_limit_price == current_side_price:
        return None

    # change limit
    new_limit_price = current_side_price

    return new_limit_price


def file_log_report_market_order(log, broker_order_with_controls):
    ticker_object = broker_order_with_controls.ticker
    current_tick = str(ticker_object.current_tick())

    log_report = "Market order execution current tick %s" % current_tick

    log.msg(log_report)
