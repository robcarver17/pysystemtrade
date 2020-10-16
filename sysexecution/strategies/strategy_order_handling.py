"""
Called from sysproduction code in a while loop, each time it runs loops over strategies
For each strategy gets the required trades per instrument
It then passes these to the 'virtual' order queue
So called because it deals with instrument level trades, not contract implementation
"""

from syscore.objects import zero_order

from syscore.objects import success, failure
from sysproduction.data.positions import diagPositions
from sysproduction.data.orders import dataOrders
from sysproduction.data.controls import diagOverrides, dataLocks, dataPositionLimits


class orderGeneratorForStrategy(object):
    """

    Order generators are strategy specific but have common methods used by the order handler

    """

    def __init__(self, data, strategy_name):

        self.strategy_name = strategy_name
        self.data = data

    def get_and_place_orders(self):
        # THIS IS THE MAIN FUNCTION THAT IS RUN
        data = self.data
        self.setup_before_placing(data)
        order_list = self.get_required_orders()
        order_list_with_overrides = self.apply_overrides(order_list)
        self.submit_order_list(order_list_with_overrides)

        return None

    def setup_before_placing(self, data):
        data_orders = dataOrders(data)
        self.data = data
        self.log = data.log
        self.data_orders = data_orders

    @property
    def order_stack(self):
        return self.data_orders.instrument_stack()

    def get_actual_positions_for_strategy(self):
        """
        Actual positions held by a strategy

        Useful to know, usually

        :return: dict, keys are instrument codes, values are positions
        """
        data = self.data
        strategy_name = self.strategy_name

        diag_positions = diagPositions(data)
        list_of_instruments = (
            diag_positions.get_list_of_instruments_for_strategy_with_position(
                strategy_name
            )
        )
        actual_positions = dict(
            [
                (
                    instrument_code,
                    diag_positions.get_position_for_strategy_and_instrument(
                        strategy_name, instrument_code
                    ),
                )
                for instrument_code in list_of_instruments
            ]
        )
        return actual_positions

    def get_required_orders(self):
        raise Exception(
            "Need to inherit with a specific method for your type of strategy"
        )

    def apply_overrides(self, order_list):
        new_order_list = [
            self.apply_overrides_for_instrument_and_strategy(proposed_order)
            for proposed_order in order_list
        ]

        return new_order_list

    def apply_overrides_for_instrument_and_strategy(self, proposed_order):
        """
        Apply an override to a trade

        :param strategy_name: str
        :param instrument_code: str
        :return: int, updated position
        """

        diag_overrides = diagOverrides(self.data)
        diag_positions = diagPositions(self.data)

        strategy_name = proposed_order.strategy_name
        instrument_code = proposed_order.instrument_code

        original_position = diag_positions.get_position_for_strategy_and_instrument(
            strategy_name, instrument_code)

        override = diag_overrides.get_cumulative_override_for_strategy_and_instrument(
            strategy_name, instrument_code)
        revised_order = override.apply_override(
            original_position, proposed_order)

        if revised_order.trade != proposed_order.trade:
            self.log.msg(
                "%s/%s trade change from %d to %d because of override %s"
                % (
                    strategy_name,
                    instrument_code,
                    revised_order.trade,
                    proposed_order.trade,
                    str(override),
                ),
                strategy_name=strategy_name,
                instrument_code=instrument_code,
            )

        return revised_order

    def submit_order_list(self, order_list):
        data_lock = dataLocks(self.data)
        for order in order_list:
            # try:
            # we allow existing orders to be modified
            log = order.log_with_attributes(self.log)
            log.msg("Required order %s" % str(order))

            instrument_locked = data_lock.is_instrument_locked(
                order.instrument_code)
            if instrument_locked:
                log.msg("Instrument locked, not submitting")
                continue
            self.submit_order(order)

        return success

    def submit_order(self, order):
        log = order.log_with_attributes(self.log)
        cut_down_order = self.adjust_order_for_position_limits(order)
        if cut_down_order.is_zero_trade():
            ## nothing to do
            return failure

        order_id = self.order_stack.put_order_on_stack(cut_down_order)
        if isinstance(order_id, int):
            log.msg(
                "Added order %s to instrument order stack with order id %d"
                % (str(order), order_id),
                instrument_order_id=order_id,
            )
        else:
            order_error_object = order_id
            if order_error_object is zero_order:
                # To be expected unless modifying an existing order
                log.msg("Ignoring zero order %s" % str(order))

            else:
                log.warn(
                    "Could not put order %s on instrument order stack, error: %s" %
                    (str(order), str(order_error_object)))

    def adjust_order_for_position_limits(self, order):

        log = order.log_with_attributes(self.log)

        data_position_limits = dataPositionLimits(self.data)
        cut_down_order = data_position_limits.cut_down_proposed_instrument_trade_okay(order)

        if cut_down_order.trade != order.trade:
            if cut_down_order.is_zero_trade():
                ## at position limit, can't do anything
                log.warn("Can't trade at all because of position limits %s" % str(order))
            else:
                log.warn("Can't do full trade of %s because of position limits, can only do %s" %
                         (str(order), str(cut_down_order.trade)))

        return cut_down_order