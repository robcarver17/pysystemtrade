import datetime
from copy import copy

from syscore.objects import missing_order
from sysexecution.order_stacks.order_stack import orderStackData, missingOrder
from sysexecution.trade_qty import tradeQuantity
from sysexecution.fill_price import fillPrice
from sysexecution.orders.contract_orders import contractOrder

class contractOrderStackData(orderStackData):
    def _name(self):
        return "Contract order stack"

    def manual_fill_for_order_id(
        self, order_id: int,
            fill_qty: tradeQuantity,
            filled_price: fillPrice=None,
            fill_datetime: datetime.datetime=None
    ):
        self.change_fill_quantity_for_order(
            order_id, fill_qty, filled_price=filled_price, fill_datetime=fill_datetime)

        # all good need to show it was a manual fill
        order = self.get_order_with_id_from_stack(order_id)
        order.manual_fill = True
        self._change_order_on_stack(order_id, order)


    def add_controlling_algo_ref(self, order_id: int,
                                 control_algo_ref: str):
        """

        :param order_id: int
        :param control_algo_ref: str or None
        :return:
        """
        if control_algo_ref is None:
            return self.release_order_from_algo_control(order_id)

        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            error_msg ="Can't add controlling ago as order %d doesn't exist" % order_id
            self.log.warn(error_msg)
            raise missingOrder(error_msg)

        try:
            modified_order = copy(existing_order)
            modified_order.add_controlling_algo_ref(control_algo_ref)
            self._change_order_on_stack(order_id, modified_order)
        except Exception as e:
            log = existing_order.log_with_attributes(self.log)
            error_msg = "%s couldn't add controlling algo %s to order %d"  % \
                        (str(e), control_algo_ref, order_id)
            log.warn(error_msg)
            raise Exception(error_msg)

    def release_order_from_algo_control(self, order_id: int):

        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            error_msg ="Can't add controlling ago as order %d doesn't exist" % order_id
            self.log.warn(error_msg)
            raise missingOrder(error_msg)

        order_is_not_controlled = not existing_order.is_order_controlled_by_algo()
        if order_is_not_controlled:
            # No change required
            return None

        try:
            modified_order = copy(existing_order)
            modified_order.release_order_from_algo_control()
            self._change_order_on_stack(order_id, modified_order)
        except Exception as e:
            log = existing_order.log_with_attributes(self.log)
            error_msg = "%s couldn't remove controlling algo from order %d" % \
                        (str(e), order_id)
            log.warn(error_msg)
            raise Exception(error_msg)

    def get_order_with_id_from_stack(self, order_id: int) -> contractOrder:
        # probably will be overriden in data implementation
        # only here so the appropriate type is shown as being returned

        order = self.stack.get(order_id, missing_order)

        return order
