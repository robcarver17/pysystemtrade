import datetime
from copy import copy

from syscore.objects import (
    missing_order,
    success,
    failure,
    locked_order,
    duplicate_order,
    no_order_id,
    no_children,
    no_parent,
    missing_contract,
    missing_data,
    rolling_cant_trade,
    ROLL_PSEUDO_STRATEGY,
    missing_order,
    order_is_in_status_reject_modification,
    order_is_in_status_finished,
    locked_order,
    order_is_in_status_modified,
    resolve_function,
)
from syscore.genutils import quickTimer
from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysproduction.data.broker import dataBroker


class stackHandlerCancelAndModify(stackHandlerCore):
    def cancel_and_confirm_all_broker_orders(
        self, log_critical_on_timeout=False, wait_time_seconds=60
    ):
        """
        Try cancelling all our orders

        We send the cancellations, and then poll for confirmation

        If no cancellation comes, then we may send an email

        :param log_critical_on_timeout: if the cancellation doesn't come through in time, log critical error
        :param wait_time_seconds: Time after cancellation to give up (and send email)
        :return: success or failure
        """
        list_of_broker_orders = self.cancel_all_broker_orders()
        result = self.check_all_orders_cancelled_with_timeout(
            list_of_broker_orders, wait_time_seconds=wait_time_seconds
        )
        if result is failure:
            # We don't wait for a confirmation
            if log_critical_on_timeout:
                self.critical_cancel_log(list_of_broker_orders)

        return result

    def cancel_all_broker_orders(self):
        list_of_broker_order_ids = self.broker_stack.get_list_of_order_ids()
        list_of_broker_orders = []
        for broker_order_id in list_of_broker_order_ids:
            broker_order = self.cancel_broker_order(broker_order_id)
            if broker_order is not missing_order:
                list_of_broker_orders.append(broker_order)

        return list_of_broker_orders

    def cancel_broker_order(self, broker_order_id):
        broker_order = self.broker_stack.get_order_with_id_from_stack(
            broker_order_id)
        if broker_order is missing_order:
            return missing_order

        if broker_order.fill_equals_desired_trade():
            # no need to cancel
            return missing_order

        log = broker_order.log_with_attributes(self.log)

        data_broker = dataBroker(self.data)

        log.msg("Cancelling order on stack %s" % str(broker_order))
        data_broker.cancel_order_on_stack(broker_order)

        return broker_order

    def check_all_orders_cancelled_with_timeout(
        self, list_of_broker_orders, wait_time_seconds=60
    ):

        timer = quickTimer(wait_time_seconds)
        result = failure
        while timer.unfinished:
            list_of_broker_orders = self.check_all_orders_cancelled(
                list_of_broker_orders
            )
            if len(list_of_broker_orders) == 0:
                result = success
                break

        return result

    def check_all_orders_cancelled(self, list_of_broker_orders):
        new_list_of_orders = copy(list_of_broker_orders)
        for broker_order in list_of_broker_orders:
            # if an order is cancelled, remove from list
            order_cancelled = self.check_order_cancelled(broker_order)
            if order_cancelled:
                log = broker_order.log_with_attributes(self.log)
                new_list_of_orders.remove(broker_order)
                log.msg("Order %s succesfully cancelled" % broker_order)

        return new_list_of_orders

    def check_order_cancelled(self, broker_order):

        data_broker = dataBroker(self.data)
        check_cancelled = data_broker.check_order_is_cancelled(broker_order)

        return check_cancelled

    def critical_cancel_log(self, list_of_broker_orders):
        for broker_order in list_of_broker_orders:
            log = broker_order.log_with_attributes(self.log)
            log.critical(
                "Broker order %s could not be cancelled within time limit; might be a position break" %
                broker_order)
