"""
Simplest possible execution method, one market order
"""
from syscore.objects import missing_order
from sysproduction.data.broker import dataBroker

from sysexecution.algos.algo import Algo
from sysexecution.algos.common_functions import (
    post_trade_processing,
    MESSAGING_FREQUENCY,
    cancel_order,
    file_log_report_market_order,
)

SIZE_LIMIT = 1
ORDER_TIME_OUT = 600


class algoMarket(Algo):
    """
    Simplest possible execution algo
    Submits a single market order for the entire quantity

    """

    def submit_trade(self):
        broker_order_with_controls = prepare_and_submit_trade(
            self.data, self.contract_order
        )
        if broker_order_with_controls is missing_order:
            # something went wrong
            return missing_order

        return broker_order_with_controls

    def manage_trade(self, broker_order_with_controls):
        data = self.data
        broker_order_with_controls = manage_trade(
            data, broker_order_with_controls)
        broker_order_with_controls = post_trade_processing(
            data, broker_order_with_controls
        )

        return broker_order_with_controls


def prepare_and_submit_trade(data, contract_order):
    log = contract_order.log_with_attributes(data.log)

    data_broker = dataBroker(data)

    cut_down_contract_order = contract_order.order_with_min_size(SIZE_LIMIT)
    if cut_down_contract_order.trade != contract_order.trade:
        log.msg(
            "Cut down order to size %s from %s because of algo size limit"
            % (str(contract_order.trade), str(cut_down_contract_order.trade))
        )

    broker_order_with_controls = (
        data_broker.get_and_submit_broker_order_for_contract_order(
            cut_down_contract_order, order_type="market"
        )
    )

    return broker_order_with_controls


def manage_trade(data, broker_order_with_controls):
    log = broker_order_with_controls.order.log_with_attributes(data.log)
    data_broker = dataBroker(data)

    trade_open = True
    log.msg("Managing trade %s with market order" %
            str(broker_order_with_controls.order))
    while trade_open:
        if broker_order_with_controls.message_required(
            messaging_frequency=MESSAGING_FREQUENCY
        ):
            file_log_report_market_order(log, broker_order_with_controls)

        order_completed = broker_order_with_controls.completed()
        order_timeout = (
            broker_order_with_controls.seconds_since_submission() > ORDER_TIME_OUT)
        order_cancelled = data_broker.check_order_is_cancelled_given_control_object(
            broker_order_with_controls)
        if order_completed:
            log.msg("Trade completed")
            break

        if order_timeout:
            log.msg("Run out of time: cancelling")
            broker_order_with_controls = cancel_order(
                data, broker_order_with_controls)
            break

        if order_cancelled:
            log.warn("Order has been cancelled: not by algo!")
            break

    return broker_order_with_controls
