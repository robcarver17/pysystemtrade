"""
This is the original 'best execution' algo I used in my legacy system
"""
from typing import Union

from syscore.constants import market_closed
from syscore.exceptions import missingData
from sysexecution.orders.named_order_objects import missing_order

from sysdata.data_blob import dataBlob
from sysexecution.algos.algo import Algo, limit_price_from_offside_price
from sysexecution.algos.common_functions import (
    post_trade_processing,
    MESSAGING_FREQUENCY,
    cancel_order,
    set_limit_price,
    check_current_limit_price_at_inside_spread,
    file_log_report_market_order,
    limit_price_is_at_inside_spread,
)
from sysexecution.tick_data import tickerObject, analysisTick
from sysexecution.order_stacks.broker_order_stack import orderWithControls
from sysexecution.orders.broker_orders import (
    market_order_type,
    limit_order_type,
    brokerOrder,
)
from sysexecution.orders.contract_orders import best_order_type, contractOrder

from syslogdiag.logger import logger

from sysproduction.data.broker import dataBroker

# Here are the algo parameters
# Hard coded; if you want to try different parameters make a hard copy and
# give it a different reference

# delay times
PASSIVE_TIME_OUT = 300
TOTAL_TIME_OUT = 600

# Don't trade with an algo in last 30 minutes
HOURS_BEFORE_MARKET_CLOSE_TO_SWITCH_TO_MARKET = 0.5

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

    def submit_trade(self) -> orderWithControls:
        placed_broker_order_with_controls = self.prepare_and_submit_trade()
        if placed_broker_order_with_controls is missing_order:
            return missing_order

        return placed_broker_order_with_controls

    def manage_trade(
        self, placed_broker_order_with_controls: orderWithControls
    ) -> orderWithControls:

        data = self.data
        placed_broker_order_with_controls = self.manage_live_trade(
            placed_broker_order_with_controls
        )
        placed_broker_order_with_controls = post_trade_processing(
            data, placed_broker_order_with_controls
        )

        return placed_broker_order_with_controls

    def prepare_and_submit_trade(self) -> orderWithControls:

        data = self.data
        contract_order = self.contract_order
        log = contract_order.log_with_attributes(data.log)

        ## check order type is 'best' not 'limit' or 'market'
        if not contract_order.order_type == best_order_type:
            log.critical(
                "Order has been allocated to algo 'original-best' but order type is %s"
                % str(contract_order.order_type)
            )
            return missing_order

        cut_down_contract_order = (
            contract_order.reduce_trade_size_proportionally_so_smallest_leg_is_max_size(
                SIZE_LIMIT
            )
        )
        if cut_down_contract_order.trade != contract_order.trade:
            log.msg(
                "Cut down order to size %s from %s because of algo size limit"
                % (str(contract_order.trade), str(cut_down_contract_order.trade))
            )

        ticker_object = self.data_broker.get_ticker_object_for_order(
            cut_down_contract_order
        )
        try:
            okay_to_do_limit_trade = limit_trade_viable(
                ticker_object=ticker_object,
                data=data,
                order=cut_down_contract_order,
                log=log,
            )
        except missingData:
            ## Safer not to trade at all
            return missing_order

        if okay_to_do_limit_trade:

            # create and issue limit order
            broker_order_with_controls = (
                self.get_and_submit_broker_order_for_contract_order(
                    cut_down_contract_order,
                    order_type=limit_order_type,
                    limit_price_from=limit_price_from_offside_price,
                    ticker_object=ticker_object,
                )
            )
        else:
            # do a market order
            log.msg("Conditions are wrong so doing market trade instead of limit trade")
            broker_order_with_controls = (
                self.get_and_submit_broker_order_for_contract_order(
                    cut_down_contract_order, order_type=market_order_type
                )
            )

        return broker_order_with_controls

    def manage_live_trade(
        self, broker_order_with_controls_and_order_id: orderWithControls
    ) -> orderWithControls:

        data = self.data
        log = broker_order_with_controls_and_order_id.order.log_with_attributes(
            data.log
        )
        data_broker = dataBroker(data)

        trade_open = True
        is_aggressive = False
        log.msg(
            "Managing trade %s with algo 'original-best'"
            % str(broker_order_with_controls_and_order_id.order)
        )

        is_limit_trade = (
            broker_order_with_controls_and_order_id.order.order_type == limit_order_type
        )

        while trade_open:
            if broker_order_with_controls_and_order_id.message_required(
                messaging_frequency_seconds=MESSAGING_FREQUENCY
            ):
                file_log_report(
                    log, is_aggressive, broker_order_with_controls_and_order_id
                )

            if is_limit_trade:
                if is_aggressive:
                    ## aggressive keep limit price in line
                    set_aggressive_limit_price(
                        data, broker_order_with_controls_and_order_id
                    )
                else:
                    # passive limit trade
                    reason_to_switch = reason_to_switch_to_aggressive(
                        data=data,
                        broker_order_with_controls=broker_order_with_controls_and_order_id,
                        log=log,
                    )
                    need_to_switch = required_to_switch_to_aggressive(reason_to_switch)

                    if need_to_switch:
                        log.msg("Switch to aggressive because %s" % reason_to_switch)
                        is_aggressive = True
            else:
                # market trade nothing to do
                pass

            order_completed = broker_order_with_controls_and_order_id.completed()

            order_timeout = (
                broker_order_with_controls_and_order_id.seconds_since_submission()
                > TOTAL_TIME_OUT
            )

            order_cancelled = data_broker.check_order_is_cancelled_given_control_object(
                broker_order_with_controls_and_order_id
            )

            if order_completed:
                log.msg("Trade completed")
                break

            if order_timeout:
                log.msg("Run out of time: cancelling")
                broker_order_with_controls_and_order_id = cancel_order(
                    data, broker_order_with_controls_and_order_id
                )
                break

            if order_cancelled:
                log.warn("Order has been cancelled: not by algo")
                break

        return broker_order_with_controls_and_order_id


def limit_trade_viable(
    data: dataBlob, order: contractOrder, ticker_object: tickerObject, log: logger
) -> bool:

    # no point doing limit order if we've got imbalanced size issues, as we'd
    # switch to aggressive immediately
    raise_adverse_size_issue = adverse_size_issue(
        ticker_object, wait_for_valid_tick=True, log=log
    )

    if raise_adverse_size_issue:
        log.msg("Limit trade not viable")
        return False

    # or if not enough time left
    if is_market_about_to_close(data, order=order, log=log):

        log.msg(
            "Market about to close or stack handler nearly close - doing market order"
        )
        return False

    return True


no_need_to_switch = "_NO_NEED_TO_SWITCH"


def file_log_report(
    log, is_aggressive: bool, broker_order_with_controls: orderWithControls
):
    limit_trade = broker_order_with_controls.order.order_type == limit_order_type
    if limit_trade:
        file_log_report_limit_order(log, is_aggressive, broker_order_with_controls)
    else:
        file_log_report_market_order(log, broker_order_with_controls)


def file_log_report_limit_order(
    log, is_aggressive: bool, broker_order_with_controls: orderWithControls
):

    if is_aggressive:
        agg_txt = "Aggressive"
    else:
        agg_txt = "Passive"

    limit_price = broker_order_with_controls.order.limit_price
    broker_limit_price = broker_order_with_controls.broker_limit_price()

    ticker_object = broker_order_with_controls.ticker
    current_tick = str(ticker_object.current_tick())

    log_report = "%s execution with limit price desired:%f actual:%f last tick %s" % (
        agg_txt,
        limit_price,
        broker_limit_price,
        current_tick,
    )

    log.msg(log_report)


def reason_to_switch_to_aggressive(
    data: dataBlob, broker_order_with_controls: orderWithControls, log: logger
) -> str:
    ticker_object = broker_order_with_controls.ticker

    too_much_time = (
        broker_order_with_controls.seconds_since_submission() > PASSIVE_TIME_OUT
    )
    adverse_price = ticker_object.adverse_price_movement_vs_reference()

    try:
        adverse_size = adverse_size_issue(
            ticker_object, wait_for_valid_tick=False, log=log
        )
    except missingData:
        adverse_size = True

    market_about_to_close = is_market_about_to_close(
        data=data, order=broker_order_with_controls, log=log
    )

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
    elif market_about_to_close:
        return "Market is closing soon or stack handler will end soon"

    return no_need_to_switch


def is_market_about_to_close(
    data: dataBlob,
    order: Union[brokerOrder, contractOrder, orderWithControls],
    log: logger,
) -> bool:
    data_broker = dataBroker(data)
    short_of_time = data_broker.less_than_N_hours_of_trading_left_for_contract(
        order.futures_contract,
        N_hours=HOURS_BEFORE_MARKET_CLOSE_TO_SWITCH_TO_MARKET,
    )

    if short_of_time is market_closed:
        log.warn("Market has closed for active limit order %s!" % str(order))
        return True

    return short_of_time


def required_to_switch_to_aggressive(reason):
    if reason == no_need_to_switch:
        return False
    else:
        return True


def adverse_size_issue(
    ticker_object: tickerObject, log: logger, wait_for_valid_tick=False
) -> bool:
    if wait_for_valid_tick:
        current_tick_analysis = (
            ticker_object.wait_for_valid_bid_and_ask_and_analyse_current_tick()
        )
    else:
        current_tick_analysis = ticker_object.current_tick_analysis

    latest_imbalance_ratio_exceeded = _is_imbalance_ratio_exceeded(
        current_tick_analysis, log=log
    )
    insufficient_size_on_our_preferred_side = (
        _is_insufficient_size_on_our_preferred_side(
            ticker_object, current_tick_analysis, log=log
        )
    )

    if latest_imbalance_ratio_exceeded and insufficient_size_on_our_preferred_side:
        return True
    else:
        return False


def _is_imbalance_ratio_exceeded(
    current_tick_analysis: analysisTick, log: logger
) -> bool:
    latest_imbalance_ratio = current_tick_analysis.imbalance_ratio
    latest_imbalance_ratio_exceeded = latest_imbalance_ratio > IMBALANCE_THRESHOLD

    if latest_imbalance_ratio_exceeded:
        log.msg(
            "Imbalance ratio for ticker %s %f exceeds threshold %f"
            % (str(current_tick_analysis), latest_imbalance_ratio, IMBALANCE_THRESHOLD)
        )

    return latest_imbalance_ratio_exceeded


def _is_insufficient_size_on_our_preferred_side(
    ticker_object: tickerObject, current_tick_analysis: analysisTick, log: logger
) -> bool:
    abs_size_we_wish_to_trade = abs(ticker_object.qty)
    size_we_require_to_trade_limit = IMBALANCE_ADJ_FACTOR * abs_size_we_wish_to_trade
    available_size_on_our_preferred_side = abs(current_tick_analysis.side_qty)

    insufficient_size_on_our_preferred_side = (
        available_size_on_our_preferred_side < size_we_require_to_trade_limit
    )

    if insufficient_size_on_our_preferred_side:
        log.msg(
            "On ticker %s we require size of %f (our trade %f * adjustment %f) for a limit order but only %f available"
            % (
                str(current_tick_analysis),
                size_we_require_to_trade_limit,
                abs_size_we_wish_to_trade,
                IMBALANCE_ADJ_FACTOR,
                available_size_on_our_preferred_side,
            )
        )

    return insufficient_size_on_our_preferred_side


def set_aggressive_limit_price(
    data: dataBlob, broker_order_with_controls: orderWithControls
) -> orderWithControls:
    limit_trade = broker_order_with_controls.order.order_type == limit_order_type
    if not limit_trade:
        # market trade, don't bother
        return broker_order_with_controls

    new_limit_price = check_current_limit_price_at_inside_spread(
        broker_order_with_controls
    )
    if new_limit_price is limit_price_is_at_inside_spread:
        pass
    else:
        broker_order_with_controls = set_limit_price(
            data, broker_order_with_controls, new_limit_price
        )

    return broker_order_with_controls
