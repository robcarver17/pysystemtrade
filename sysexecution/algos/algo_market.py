"""
Simplest possible execution method, one market order
"""
from copy import copy
from sysexecution.orders.named_order_objects import missing_order
from sysproduction.data.broker import dataBroker

from sysexecution.algos.algo import Algo
from sysexecution.algos.common_functions import (
    post_trade_processing,
    MESSAGING_FREQUENCY,
    cancel_order,
    file_log_report_market_order,
)
from sysdata.data_blob import dataBlob
from sysexecution.orders.contract_orders import contractOrder
from sysexecution.order_stacks.broker_order_stack import orderWithControls
from sysexecution.orders.broker_orders import market_order_type

SIZE_LIMIT = 1
ORDER_TIME_OUT = 600


class algoMarket(Algo):
    """
    Simplest possible execution algo
    Submits a single market order for the entire quantity

    """

    def submit_trade(self) -> orderWithControls:
        broker_order_with_controls = self.prepare_and_submit_trade()
        if broker_order_with_controls is missing_order:
            # something went wrong
            return missing_order

        return broker_order_with_controls

    def manage_trade(
        self, broker_order_with_controls: orderWithControls
    ) -> orderWithControls:
        broker_order_with_controls = self.manage_live_trade(broker_order_with_controls)
        broker_order_with_controls = post_trade_processing(
            self.data, broker_order_with_controls
        )

        return broker_order_with_controls

    def prepare_and_submit_trade(self):
        contract_order = self.contract_order
        log = contract_order.log_with_attributes(self.data.log)

        if contract_order.panic_order:
            log.msg("PANIC ORDER! DON'T RESIZE AND DO ENTIRE TRADE")
            cut_down_contract_order = copy(contract_order)
        else:
            cut_down_contract_order = contract_order.reduce_trade_size_proportionally_so_smallest_leg_is_max_size(
                SIZE_LIMIT
            )

        if cut_down_contract_order.trade != contract_order.trade:
            log.msg(
                "Cut down order to size %s from %s because of algo size limit"
                % (str(contract_order.trade), str(cut_down_contract_order.trade))
            )

        broker_order_with_controls = (
            self.get_and_submit_broker_order_for_contract_order(
                cut_down_contract_order, order_type=market_order_type
            )
        )

        return broker_order_with_controls

    def manage_live_trade(
        self, broker_order_with_controls: orderWithControls
    ) -> orderWithControls:
        log = broker_order_with_controls.order.log_with_attributes(self.data.log)
        data_broker = self.data_broker

        trade_open = True
        log.msg(
            "Managing trade %s with market order"
            % str(broker_order_with_controls.order)
        )
        while trade_open:
            log_message_required = broker_order_with_controls.message_required(
                messaging_frequency_seconds=MESSAGING_FREQUENCY
            )
            if log_message_required:
                file_log_report_market_order(log, broker_order_with_controls)

            is_order_completed = broker_order_with_controls.completed()
            is_order_timeout = (
                broker_order_with_controls.seconds_since_submission() > ORDER_TIME_OUT
            )
            is_order_cancelled = (
                data_broker.check_order_is_cancelled_given_control_object(
                    broker_order_with_controls
                )
            )
            if is_order_completed:
                log.msg("Trade completed")
                break

            if is_order_timeout:
                log.msg("Run out of time to execute: cancelling")
                broker_order_with_controls = cancel_order(
                    self.data, broker_order_with_controls
                )
                break

            if is_order_cancelled:
                log.warn("Order has been cancelled apparently by broker: not by algo!")
                break

        return broker_order_with_controls
