from copy import copy
from syscore.objects import (
    missing_order,
    resolve_function,
)
from sysproduction.data.controls import dataTradeLimits

from sysexecution.algos.allocate_algo_to_order import (
    check_and_if_required_allocate_algo_to_single_contract_order,
)

from sysexecution.orders.contract_orders import contractOrder, limit_order_type
from sysexecution.orders.broker_orders import brokerOrder
from sysexecution.order_stacks.instrument_order_stack import instrumentOrder
from sysexecution.order_stacks.broker_order_stack import orderWithControls
from sysexecution.algos.algo import Algo
from sysexecution.stack_handler.fills import stackHandlerForFills
from sysproduction.data.controls import dataLocks
from sysproduction.data.broker import dataBroker


class stackHandlerCreateBrokerOrders(stackHandlerForFills):
    def create_broker_orders_from_contract_orders(self):
        """
        Create broker orders from contract orders. These become child orders of the contract parent.

        Depending on the algo used, multiple broker orders might be created
        This could represent failed orders or iceberg type algos that do partial fills

        Algos are 'fire and forget' (the order is issued then the algo closes down) eg simple market order
           or 'active' (the algo controls the order until it is released)

        We need to create a new broker order and launch a new algo if:

        - the order is not completely filled AND
        - the order is not currently controlled by an algo

        :return: None
        """
        list_of_contract_order_ids = self.contract_stack.get_list_of_order_ids()
        for contract_order_id in list_of_contract_order_ids:

            self.create_broker_order_for_contract_order(contract_order_id)

    def create_broker_order_for_contract_order(self, contract_order_id: int):

        original_contract_order = self.contract_stack.get_order_with_id_from_stack(
            contract_order_id
        )

        contract_order_to_trade = self.preprocess_contract_order(
            original_contract_order
        )

        if contract_order_to_trade is missing_order:
            # Empty order not submitting to algo
            return None

        algo_instance_and_placed_broker_order_with_controls = self.send_to_algo(
            contract_order_to_trade
        )

        if algo_instance_and_placed_broker_order_with_controls is missing_order:
            # something gone wrong with execution
            return missing_order

        (
            algo_instance,
            placed_broker_order_with_controls,
        ) = algo_instance_and_placed_broker_order_with_controls

        broker_order_with_controls_and_order_id = self.add_trade_to_database(
            placed_broker_order_with_controls
        )

        if algo_instance.blocking_algo_requires_management:

            completed_broker_order_with_controls = algo_instance.manage_trade(
                broker_order_with_controls_and_order_id
            )

            self.post_trade_processing(completed_broker_order_with_controls)
        else:
            ### Hopefully order will come through...
            pass

    def preprocess_contract_order(
        self, original_contract_order: contractOrder
    ) -> contractOrder:

        if original_contract_order is missing_order:
            # weird race condition
            return missing_order

        if original_contract_order.fill_equals_desired_trade():
            return missing_order

        if original_contract_order.is_order_controlled_by_algo():
            # already being traded by an active algo
            return missing_order

        if original_contract_order.panic_order:
            ## Do no further checks or resizing whatsoever!
            return original_contract_order

        data_broker = self.data_broker

        # CHECK FOR LOCKS
        data_locks = dataLocks(self.data)
        instrument_locked = data_locks.is_instrument_locked(
            original_contract_order.instrument_code
        )

        market_closed = not (
            data_broker.is_contract_okay_to_trade(
                original_contract_order.futures_contract
            )
        )
        if instrument_locked or market_closed:
            # we don't log to avoid spamming
            # print("market is closed for order %s" % str(original_contract_order))
            return missing_order

        # RESIZE
        contract_order_to_trade = self.size_contract_order(original_contract_order)

        return contract_order_to_trade

    def size_contract_order(
        self, original_contract_order: contractOrder
    ) -> contractOrder:
        # We can deal with partially filled contract orders: that's how hard we
        # are!
        remaining_contract_order = (
            original_contract_order.create_order_with_unfilled_qty()
        )

        if original_contract_order.order_type == limit_order_type:
            ## NO SIZE LIMITS APPLY TO LIMIT ORDERS
            return remaining_contract_order

        # Check the order doesn't breach trade limits
        contract_order_after_trade_limits = self.apply_trade_limits_to_contract_order(
            remaining_contract_order
        )

        contract_order_to_trade = self.liquidity_size_contract_order(
            contract_order_after_trade_limits
        )

        if contract_order_to_trade is missing_order:
            return missing_order

        if contract_order_to_trade.fill_equals_desired_trade():
            # Nothing left to trade
            return missing_order

        return contract_order_to_trade

    def apply_trade_limits_to_contract_order(
        self, proposed_order: contractOrder
    ) -> contractOrder:
        log = proposed_order.log_with_attributes(self.log)
        data_trade_limits = dataTradeLimits(self.data)

        instrument_strategy = proposed_order.instrument_strategy

        # proposed_order.trade.total_abs_qty() is a scalar, returns a scalar
        maximum_abs_qty = (
            data_trade_limits.what_trade_is_possible_for_strategy_instrument(
                instrument_strategy, proposed_order.trade
            )
        )

        contract_order_after_trade_limits = (
            proposed_order.change_trade_size_proportionally_to_meet_abs_qty_limit(
                maximum_abs_qty
            )
        )

        if contract_order_after_trade_limits.trade != proposed_order.trade:
            log.msg(
                "%s trade change from %s to %s because of trade limits"
                % (
                    proposed_order.key,
                    str(proposed_order.trade),
                    str(contract_order_after_trade_limits.trade),
                )
            )

        return contract_order_after_trade_limits

    def liquidity_size_contract_order(
        self, contract_order_after_trade_limits: contractOrder
    ) -> contractOrder:

        data_broker = self.data_broker
        log = contract_order_after_trade_limits.log_with_attributes(self.log)

        # check liquidity, and if necessary carve up order
        # Note for spread orders we check liquidity in the component markets
        liquid_qty = (
            data_broker.get_largest_offside_liquid_size_for_contract_order_by_leg(
                contract_order_after_trade_limits
            )
        )

        if liquid_qty != contract_order_after_trade_limits.trade:
            log.msg(
                "Cut down order to size %s from %s because of liquidity"
                % (str(liquid_qty), str(contract_order_after_trade_limits.trade))
            )

        if liquid_qty.equals_zero():
            return missing_order

        contract_order_to_trade = contract_order_after_trade_limits.replace_required_trade_size_only_use_for_unsubmitted_trades(
            liquid_qty
        )

        return contract_order_to_trade

    def send_to_algo(
        self, contract_order_to_trade: contractOrder
    ) -> (Algo, orderWithControls):

        log = contract_order_to_trade.log_with_attributes(self.log)
        instrument_order = self.get_parent_of_contract_order(contract_order_to_trade)

        contract_order_to_trade_with_algo_set = (
            check_and_if_required_allocate_algo_to_single_contract_order(
                data=self.data,
                contract_order=contract_order_to_trade,
                instrument_order=instrument_order,
            )
        )

        log.msg(
            "Sending order %s to algo %s"
            % (
                str(contract_order_to_trade_with_algo_set),
                contract_order_to_trade_with_algo_set.algo_to_use,
            )
        )

        algo_class_to_call = self.add_controlling_algo_to_order(
            contract_order_to_trade_with_algo_set
        )
        algo_instance = algo_class_to_call(
            self.data, contract_order_to_trade_with_algo_set
        )

        # THIS LINE ACTUALLY SENDS THE ORDER TO THE ALGO
        placed_broker_order_with_controls = algo_instance.submit_trade()

        if placed_broker_order_with_controls is missing_order:
            # important we do this or order will never execute
            #  if no issue here will be released once order filled
            self.contract_stack.release_order_from_algo_control(
                contract_order_to_trade_with_algo_set.order_id
            )
            return missing_order

        return algo_instance, placed_broker_order_with_controls

    def get_parent_of_contract_order(
        self, contract_order: contractOrder
    ) -> instrumentOrder:
        instrument_order_id = contract_order.parent
        parent_instrument_order = self.instrument_stack.get_order_with_id_from_stack(
            instrument_order_id
        )

        return parent_instrument_order

    def add_controlling_algo_to_order(
        self, contract_order_to_trade: contractOrder
    ) -> "function":
        # Note we don't save the algo method, but reallocate each time
        # This is useful if trading is about to finish, because we switch to market orders
        # (assuming a bunch of limit orders haven't worked out so well)

        algo_to_use_str = contract_order_to_trade.algo_to_use
        algo_method = resolve_function(algo_to_use_str)

        # This prevents another algo from trying to trade the same contract order
        # Very important to avoid multiple broker orders being issued from the
        # same contract order
        self.contract_stack.add_controlling_algo_ref(
            contract_order_to_trade.order_id, algo_to_use_str
        )

        return algo_method

    def add_trade_to_database(
        self, broker_order_with_controls: orderWithControls
    ) -> orderWithControls:
        broker_order_with_controls_and_order_id = copy(broker_order_with_controls)

        broker_order = broker_order_with_controls_and_order_id.order

        log = broker_order.log_with_attributes(self.log)
        try:
            broker_order_id = self.broker_stack.put_order_on_stack(broker_order)
        except Exception as e:
            # We've created a broker order but can't add it to the broker order database
            # Probably safest to leave the contract order locked otherwise there could be multiple
            #   broker orders issued and nobody wants that!
            error_msg = (
                "Created a broker order %s but can't add it to the order stack!! (condition %s) STACK CORRUPTED"
                % (str(broker_order), str(e))
            )
            log.critical(error_msg)
            raise Exception(error_msg)

        # set order_id (wouldn't have had one before, might be done inside db adding but make explicit)
        broker_order.order_id = broker_order_id

        # This broker order is a child of the parent contract order
        # We add 'another' child since it's valid to have multiple broker
        # orders
        contract_order_id = broker_order.parent
        self.contract_stack.add_another_child_to_order(
            contract_order_id, broker_order_id
        )

        return broker_order_with_controls_and_order_id

    def post_trade_processing(
        self, completed_broker_order_with_controls: orderWithControls
    ):

        broker_order = completed_broker_order_with_controls.order

        # update trade limits
        self.add_trade_to_trade_limits(broker_order)

        # apply fills and commissions
        self.apply_broker_order_fills_to_database(
            broker_order_id=broker_order.order_id, broker_order=broker_order
        )

        # release contract order from algo
        contract_order_id = broker_order.parent
        self.contract_stack.release_order_from_algo_control(contract_order_id)
        self.log.msg("Released contract order %s from algo control" % contract_order_id)

    def add_trade_to_trade_limits(self, executed_order: brokerOrder):

        data_trade_limits = dataTradeLimits(self.data)

        data_trade_limits.add_trade(executed_order)
