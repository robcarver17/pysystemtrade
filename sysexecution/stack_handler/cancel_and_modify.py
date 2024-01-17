from copy import copy

from sysexecution.order_stacks.order_stack import missingOrder
from sysexecution.orders.named_order_objects import missing_order
from syscore.genutils import quickTimer
from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysexecution.orders.list_of_orders import listOfOrders
from sysexecution.orders.broker_orders import brokerOrder
from sysproduction.data.broker import dataBroker


class stackHandlerCancelAndModify(stackHandlerCore):
    def cancel_and_confirm_all_broker_orders(
        self, log_critical_on_timeout: bool = False, wait_time_seconds: int = 60
    ):
        """
        Try cancelling all our orders

        We send the cancellations, and then poll for confirmation

        If no cancellation comes, then we may send an email

        :param log_critical_on_timeout: if the cancellation doesn't come through in time, log critical error
        :param wait_time_seconds: Time after cancellation to give up (and send email)
        :return: success or failure
        """
        list_of_broker_orders = (
            self.try_and_cancel_all_broker_orders_and_return_list_of_orders()
        )
        list_of_uncancelled_broker_orders = self.are_all_orders_cancelled_after_timeout(
            list_of_broker_orders, wait_time_seconds=wait_time_seconds
        )
        if len(list_of_uncancelled_broker_orders) > 0:
            # We don't wait for a confirmation
            if log_critical_on_timeout:
                self.critical_cancel_log(list_of_uncancelled_broker_orders)
        else:
            self.log.debug("All orders cancelled okay")

    def try_and_cancel_all_broker_orders_and_return_list_of_orders(
        self,
    ) -> listOfOrders:
        list_of_broker_order_ids = self.broker_stack.get_list_of_order_ids()
        list_of_broker_orders = []
        for broker_order_id in list_of_broker_order_ids:
            broker_order = self.cancel_broker_order_with_id_and_return_order(
                broker_order_id
            )
            if broker_order is not missing_order:
                list_of_broker_orders.append(broker_order)

        list_of_broker_orders = listOfOrders(list_of_broker_orders)

        return list_of_broker_orders

    def cancel_broker_order_with_id_and_return_order(
        self, broker_order_id: int
    ) -> brokerOrder:
        broker_order = self.broker_stack.get_order_with_id_from_stack(broker_order_id)

        if broker_order is missing_order:
            return missing_order

        if broker_order.fill_equals_desired_trade():
            # no need to cancel
            return missing_order

        self.log.debug(
            "Cancelling order on stack with broker %s" % str(broker_order),
            **broker_order.log_attributes(),
            method="temp",
        )

        data_broker = self.data_broker
        data_broker.cancel_order_on_stack(broker_order)

        return broker_order

    def are_all_orders_cancelled_after_timeout(
        self, list_of_broker_orders: listOfOrders, wait_time_seconds: int = 60
    ) -> listOfOrders:
        timer = quickTimer(wait_time_seconds)
        while timer.unfinished:
            list_of_broker_orders = self.list_of_orders_not_yet_cancelled(
                list_of_broker_orders
            )
            if len(list_of_broker_orders) == 0:
                break

        return list_of_broker_orders

    def list_of_orders_not_yet_cancelled(
        self, list_of_broker_orders: listOfOrders
    ) -> listOfOrders:
        new_list_of_orders = copy(list_of_broker_orders)
        for broker_order in list_of_broker_orders:
            # if an order is cancelled, remove from list
            try:
                order_is_cancelled = self.check_order_cancelled(broker_order)
            except missingOrder:
                # Maintains previous behavior by assuming an order was cancelled
                # when the corresponding IB order is not found
                order_is_cancelled = True

            if order_is_cancelled:
                new_list_of_orders.remove(broker_order)
                self.log.debug(
                    "Order %s successfully cancelled" % broker_order,
                    **broker_order.log_attributes(),
                    method="temp",
                )

        new_list_of_orders = listOfOrders(new_list_of_orders)

        return new_list_of_orders

    def check_order_cancelled(self, broker_order: brokerOrder) -> bool:
        data_broker = self.data_broker
        order_is_cancelled = data_broker.check_order_is_cancelled(broker_order)

        return order_is_cancelled

    def critical_cancel_log(self, list_of_broker_orders: listOfOrders):
        for broker_order in list_of_broker_orders:
            self.log.critical(
                "Broker order %s could not be cancelled within time limit; might be a "
                "position break" % broker_order,
                **broker_order.log_attributes(),
                method="temp",
            )
