from copy import copy

from syscore.objects import failure, missing_order, success
from sysexecution.order_stacks.order_stack import orderStackData

class contractOrderStackData(orderStackData):
    def __repr__(self):
        return "Contract order stack: %s" % str(self._stack)

    def manual_fill_for_order_id(
        self, order_id, fill_qty, filled_price=None, fill_datetime=None
    ):
        result = self.change_fill_quantity_for_order(
            order_id, fill_qty, filled_price=filled_price, fill_datetime=fill_datetime)
        if result is failure:
            return failure

        # all good need to show it was a manual fill
        order = self.get_order_with_id_from_stack(order_id)
        order.manual_fill = True
        result = self._change_order_on_stack(order_id, order)

        return result

    def add_controlling_algo_ref(self, order_id, control_algo_ref):
        """

        :param order_id: int
        :param control_algo_ref: str or None
        :return:
        """
        if control_algo_ref is None:
            return self.release_order_from_algo_control(order_id)

        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            raise Exception(
                "Can't add controlling ago as order %d doesn't exist" %
                order_id)

        try:
            modified_order = copy(existing_order)
            modified_order.add_controlling_algo_ref(control_algo_ref)
        except Exception as e:
            raise Exception(
                "%s couldn't add controlling algo %s to order %d"
                % (str(e), control_algo_ref, order_id)
            )

        result = self._change_order_on_stack(order_id, modified_order)

        if result is not success:
            raise Exception(
                "%s when trying to add controlling algo to order %d"
                % (str(result), order_id)
            )

        return success

    def release_order_from_algo_control(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            raise Exception(
                "Can't release controlling ago as order %d doesn't exist" %
                order_id)

        if not existing_order.is_order_controlled_by_algo():
            # No change required
            return success

        try:
            modified_order = copy(existing_order)
            modified_order.release_order_from_algo_control()
        except Exception as e:
            raise Exception(
                "%s couldn't release controlling algo for order %d" %
                (str(e), order_id))

        result = self._change_order_on_stack(order_id, modified_order)

        if result is not success:
            raise Exception(
                "%s when trying to add controlling algo to order %d"
                % (str(result), order_id)
            )

        return success