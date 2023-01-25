from sysexecution.orders.named_order_objects import missing_order, zero_order
from sysexecution.order_stacks.order_stack import orderStackData
from sysexecution.orders.instrument_orders import instrumentOrder
from sysexecution.orders.list_of_orders import listOfOrders
from sysexecution.trade_qty import tradeQuantity


class zeroOrderException(Exception):
    pass


class instrumentOrderStackData(orderStackData):
    @property
    def _name(self):
        return "Instrument order stack"

    def does_strategy_and_instrument_already_have_order_on_stack(
        self, strategy_name: str, instrument_code: str
    ) -> bool:
        pseudo_order = instrumentOrder(strategy_name, instrument_code, 0)
        existing_orders = (
            self._get_list_of_orderids_with_same_tradeable_object_on_stack(pseudo_order)
        )
        if existing_orders is missing_order:
            return False

        return True

    def put_manual_order_on_stack_and_return_order_id(
        self, new_order: instrumentOrder
    ) -> int:
        """
        Puts an order on the stack ignoring the usual checks

        :param new_order:
        :return: order_id or failure object
        """

        order_id_or_error = self._put_order_on_stack_and_get_order_id(new_order)

        return order_id_or_error

    def put_order_on_stack(
        self, new_order: instrumentOrder, allow_zero_orders: bool = False
    ):
        """
        Put an order on the stack, or at least try to:
        - if no existing order for this instrument/strategy, add
        - if an existing order for this instrument/strategy, put an adjusting order on

        :param new_order: Order
        :return: order_id or failure condition: duplicate_order, failure
        """

        existing_order_id_list = (
            self._get_list_of_orderids_with_same_tradeable_object_on_stack(new_order)
        )
        if existing_order_id_list is missing_order:
            # brand new trade
            result = self._put_new_order_on_stack_when_no_existing_order(
                new_order, allow_zero_orders=allow_zero_orders
            )
        else:
            # adjusting trade
            result = self._put_adjusting_order_on_stack(
                new_order, existing_order_id_list, allow_zero_orders=allow_zero_orders
            )
        return result

    def _put_new_order_on_stack_when_no_existing_order(
        self, new_order: instrumentOrder, allow_zero_orders: bool = False
    ) -> int:
        # no current order for this instrument/strategy

        log = new_order.log_with_attributes(self.log)

        if new_order.is_zero_trade() and not allow_zero_orders:
            log_msg = "Zero orders not allowed"
            log.msg(log_msg)
            raise zeroOrderException(log_msg)

        log.msg("New order %s putting on %s" % (str(new_order), str(self)))

        order_id = self._put_order_on_stack_and_get_order_id(new_order)

        return order_id

    def _put_adjusting_order_on_stack(
        self,
        new_order: instrumentOrder,
        existing_order_id_list: list,
        allow_zero_orders: bool = False,
    ) -> int:
        """
        Considering the unfilled orders already on the stack place an additional adjusting order

        :param new_order:
        :return:
        """
        log = new_order.log_with_attributes(self.log)

        existing_orders = listOfOrders(
            [
                self.get_order_with_id_from_stack(order_id)
                for order_id in existing_order_id_list
            ]
        )

        adjusted_order = calculate_adjusted_order_given_existing_orders(
            new_order, existing_orders, log
        )

        if adjusted_order.is_zero_trade() and not allow_zero_orders:
            # Trade we want is already in the system
            error_msg = "Adjusted order %s is zero, zero orders not allowed" % str(
                adjusted_order
            )
            log.warn(error_msg)
            raise zeroOrderException(error_msg)

        order_id = self._put_order_on_stack_and_get_order_id(adjusted_order)

        return order_id


def calculate_adjusted_order_given_existing_orders(
    new_order: instrumentOrder, existing_orders: listOfOrders, log
):

    desired_new_trade = new_order.trade
    (
        existing_trades,
        net_existing_trades_to_execute,
    ) = calculate_existing_trades_and_remainder(existing_orders)

    # can change sign
    residual_trade = desired_new_trade - net_existing_trades_to_execute

    adjusted_order = (
        new_order.replace_required_trade_size_only_use_for_unsubmitted_trades(
            residual_trade
        )
    )

    log.msg(
        "Already have orders %s wanted %s so putting on order for %s (%s)"
        % (
            str(existing_trades),
            str(desired_new_trade),
            str(residual_trade),
            str(adjusted_order),
        )
    )

    return adjusted_order


def calculate_existing_trades_and_remainder(
    existing_orders: listOfOrders,
) -> (tradeQuantity, tradeQuantity):
    existing_trades = [existing_order.trade for existing_order in existing_orders]

    existing_fills = [existing_order.fill for existing_order in existing_orders]

    net_existing_trades = sum(existing_trades)
    net_existing_fills = sum(existing_fills)
    net_existing_trades_to_execute = net_existing_trades - net_existing_fills

    return existing_trades, net_existing_trades_to_execute
