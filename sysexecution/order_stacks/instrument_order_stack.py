from syscore.objects import missing_order, zero_order
from sysexecution.order_stacks.order_stack import orderStackData
from sysexecution.orders.instrument_orders import instrumentOrder


class instrumentOrderStackData(orderStackData):
    def __repr__(self):
        return "Instrument order stack: %s" % str(self._stack)

    def put_manual_order_on_stack(self, new_order):
        """
        Puts an order on the stack ignoring the usual checks

        :param new_order:
        :return: order_id or failure object
        """

        order_id_or_error = self._put_order_on_stack_and_get_order_id(
            new_order)

        return order_id_or_error

    def put_order_on_stack(self, new_order, allow_zero_orders=False):
        """
        Put an order on the stack, or at least try to:
        - if no existing order for this instrument/strategy, add
        - if an existing order for this instrument/strategy, put an adjusting order on

        :param new_order: Order
        :return: order_id or failure condition: duplicate_order, failure
        """

        existing_order_id_list = self._get_order_with_same_tradeable_object_on_stack(
            new_order)
        if existing_order_id_list is missing_order:
            result = self._put_new_order_on_stack_when_no_existing_order(
                new_order, allow_zero_orders=allow_zero_orders
            )
        else:
            result = self._put_adjusting_order_on_stack(
                new_order, existing_order_id_list, allow_zero_orders=allow_zero_orders)
        return result

    def does_strategy_and_instrument_already_have_order_on_stack(
        self, strategy_name, instrument_code
    ):
        pseudo_order = instrumentOrder(strategy_name, instrument_code, 0)
        existing_orders = self._get_order_with_same_tradeable_object_on_stack(
            pseudo_order
        )
        if existing_orders is missing_order:
            return False
        return True

    def _put_new_order_on_stack_when_no_existing_order(
        self, new_order, allow_zero_orders=False
    ):
        log = new_order.log_with_attributes(self.log)

        if new_order.is_zero_trade() and not allow_zero_orders:
            log.msg("Zero orders not allowed")
            return zero_order

        # no current order for this instrument/strategy
        log.msg(
            "New order %s putting on %s" %
            (str(new_order), self.__repr__()))
        order_id_or_error = self._put_order_on_stack_and_get_order_id(
            new_order)
        return order_id_or_error

    def _put_adjusting_order_on_stack(
        self, new_order, existing_order_id_list, allow_zero_orders=False
    ):
        """
        Considering the unfilled orders already on the stack place an additional adjusting order

        :param new_order:
        :return:
        """
        log = new_order.log_with_attributes(self.log)

        existing_orders = [
            self.get_order_with_id_from_stack(order_id)
            for order_id in existing_order_id_list
        ]
        existing_trades = [
            existing_order.trade for existing_order in existing_orders]
        existing_fills = [
            existing_order.fill for existing_order in existing_orders]

        net_existing_trades = sum(existing_trades)
        net_existing_fills = sum(existing_fills)
        net_existing_trades_to_execute = net_existing_trades - net_existing_fills

        new_trade = new_order.trade

        # can change sign
        residual_trade = new_trade - net_existing_trades_to_execute

        adjusted_order = new_order.replace_required_trade_size_only_use_for_unsubmitted_trades(
            residual_trade)

        if adjusted_order.is_zero_trade() and not allow_zero_orders:
            # Trade we want is already in the system
            return zero_order

        log.msg(
            "Already have orders %s wanted %s so putting on order for %s (%s)"
            % (
                str(existing_trades),
                str(new_trade),
                str(residual_trade),
                str(adjusted_order),
            )
        )
        order_id_or_error = self._put_order_on_stack_and_get_order_id(
            adjusted_order)

        return order_id_or_error