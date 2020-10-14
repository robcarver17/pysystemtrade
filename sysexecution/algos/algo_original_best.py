"""
This is the original 'best execution' algo I used in my legacy system
"""
from syscore.objects import missing_order

from sysexecution.algos.algo import Algo
from sysexecution.algos.common_functions import (
    post_trade_processing,
    MESSAGING_FREQUENCY,
    cancel_order,
    set_limit_price,
    check_current_limit_price_at_inside_spread,
    file_log_report_market_order,
)

from sysproduction.data.broker import dataBroker

# Here are the algo parameters
# Hard coded; if you want to try different parameters make a hard copy and
# give it a different reference

# delay times
PASSIVE_TIME_OUT = 300
TOTAL_TIME_OUT = 600

# imbalance
# if more than 5 times on the bid (if we're buying) than the offer, AND less than three times our quantity on the offer,
# then go aggressive
IMBALANCE_THRESHOLD = 5
IMBALANCE_ADJ_FACTOR = 3

# we only do one contract at a time
SIZE_LIMIT = 1


class algoOriginalBest(Algo):
    """
    This is the original 'best execution' algo I used in my legacy system
    It's behaviour is described here
       https://qoppac.blogspot.com/2014/10/the-worlds-simplest-execution-algorithim.html

    """

    def submit_trade(self):
        placed_broker_order_with_controls = prepare_and_submit_trade(
            self.data, self.contract_order
        )
        if placed_broker_order_with_controls is missing_order:
            return missing_order

        return placed_broker_order_with_controls

    def manage_trade(self, placed_broker_order_with_controls):

        data = self.data
        placed_broker_order_with_controls = manage_trade(
            data, placed_broker_order_with_controls)
        placed_broker_order_with_controls = post_trade_processing(
            data, placed_broker_order_with_controls
        )

        return placed_broker_order_with_controls


def prepare_and_submit_trade(data, contract_order):

    log = contract_order.log_with_attributes(data.log)
    data_broker = dataBroker(data)

    cut_down_contract_order = contract_order.order_with_min_size(SIZE_LIMIT)
    if cut_down_contract_order.trade != contract_order.trade:
        log.msg(
            "Cut down order to size %s from %s because of algo size limit"
            % (str(contract_order.trade), str(cut_down_contract_order.trade))
        )

    ticker_object = data_broker.get_ticker_object_for_order(
        cut_down_contract_order)
    okay_to_do_limit_trade = limit_trade_viable(ticker_object)

    if okay_to_do_limit_trade:

        # create and issue limit order
        broker_order_with_controls = (
            data_broker.get_and_submit_broker_order_for_contract_order(
                cut_down_contract_order,
                order_type="limit",
                limit_price_from="offside_price",
                ticker_object=ticker_object,
            )
        )
    else:
        # do a market order
        log.msg("Conditions are wrong so doing market trade instead of limit trade")
        broker_order_with_controls = (
            data_broker.get_and_submit_broker_order_for_contract_order(
                cut_down_contract_order, order_type="market"
            )
        )

    return broker_order_with_controls


def limit_trade_viable(ticker_object):
    # no point doing limit order if we've got imbalanced size issues, as we'd
    # switch to aggressive immediately
    if adverse_size_issue(ticker_object):
        return False

    # might be other reasons...

    return True


def manage_trade(data, placed_broker_order_with_controls):
    log = placed_broker_order_with_controls.order.log_with_attributes(data.log)
    data_broker = dataBroker(data)

    trade_open = True
    aggressive = False
    log.msg(
        "Managing trade %s with algo 'original-best'"
        % str(placed_broker_order_with_controls.order)
    )

    limit_trade = placed_broker_order_with_controls.order.order_type == "limit"

    while trade_open:
        if placed_broker_order_with_controls.message_required(
            messaging_frequency=MESSAGING_FREQUENCY
        ):
            file_log_report(log, aggressive, placed_broker_order_with_controls)

        if limit_trade:
            if aggressive:
                set_aggressive_limit_price(data, placed_broker_order_with_controls)
            else:
                # passive
                reason_to_switch = switch_to_aggressive(
                    placed_broker_order_with_controls)
                if reason_to_switch is not None:
                    log.msg(
                        "Switch to aggressive because %s" %
                        reason_to_switch)
                    aggressive = True

        order_completed = placed_broker_order_with_controls.completed()
        order_timeout = (
            placed_broker_order_with_controls.seconds_since_submission() > TOTAL_TIME_OUT)
        order_cancelled = data_broker.check_order_is_cancelled_given_control_object(
            placed_broker_order_with_controls)
        if order_completed:
            log.msg("Trade completed")
            break

        if order_timeout:
            log.msg("Run out of time: cancelling")
            placed_broker_order_with_controls = cancel_order(
                data, placed_broker_order_with_controls)
            break

        if order_cancelled:
            log.warn("Order has been cancelled: not by algo")
            break

    return placed_broker_order_with_controls


def file_log_report(log, aggressive, broker_order_with_controls):
    limit_trade = broker_order_with_controls.order.order_type == "limit"
    if limit_trade:
        file_log_report_limit_order(
            log, aggressive, broker_order_with_controls)
    else:
        file_log_report_market_order(log, broker_order_with_controls)


def file_log_report_limit_order(log, aggressive, broker_order_with_controls):

    if aggressive:
        agg_txt = "Aggressive"
    else:
        agg_txt = "Passive"

    limit_price = broker_order_with_controls.order.limit_price
    broker_limit_price = broker_order_with_controls.broker_limit_price()

    ticker_object = broker_order_with_controls.ticker
    current_tick = str(ticker_object.current_tick())

    log_report = "%s execution with limit price desired:%f actual:%f last tick %s" % (
        agg_txt, limit_price, broker_limit_price, current_tick, )

    log.msg(log_report)


def switch_to_aggressive(broker_order_with_controls):
    ticker_object = broker_order_with_controls.ticker

    too_much_time = (
        broker_order_with_controls.seconds_since_submission() > PASSIVE_TIME_OUT)
    adverse_price = ticker_object.adverse_price_movement_vs_reference()
    adverse_size = adverse_size_issue(ticker_object)

    if too_much_time:
        return (
            "Time out after %f seconds"
            % broker_order_with_controls.seconds_since_submission()
        )
    elif adverse_price:
        return "Adverse price movement"
    elif adverse_size:
        return (
            "Imbalance ratio of %f exceeds threshold"
            % ticker_object.latest_imbalance_ratio()
        )

    return None


def adverse_size_issue(ticker_object):
    latest_imbalance_ratio_exceeded = (
        ticker_object.latest_imbalance_ratio() > IMBALANCE_THRESHOLD
    )
    insufficient_size_on_our_preferred_side = (
        ticker_object.last_tick_analysis.side_qty
        < abs(ticker_object.qty * IMBALANCE_ADJ_FACTOR)
    )

    if latest_imbalance_ratio_exceeded and insufficient_size_on_our_preferred_side:
        return True
    else:
        return False


def set_aggressive_limit_price(data, broker_order_with_controls):
    limit_trade = broker_order_with_controls.order.order_type == "limit"
    if not limit_trade:
        # market trade, don't bother
        return broker_order_with_controls

    new_limit_price = check_current_limit_price_at_inside_spread(
        broker_order_with_controls
    )
    if new_limit_price is not None:
        broker_order_with_controls = set_limit_price(
            data, broker_order_with_controls, new_limit_price
        )

    return broker_order_with_controls
