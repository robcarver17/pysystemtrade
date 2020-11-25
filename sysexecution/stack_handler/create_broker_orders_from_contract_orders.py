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

from sysexecution.algos.allocate_algo_to_order import (
    check_and_if_required_allocate_algo_to_single_contract_order,
)

from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysproduction.data.controls import dataLocks
from sysproduction.data.broker import dataBroker


class stackHandlerCreateBrokerOrders(stackHandlerCore):
    def create_broker_orders_from_contract_orders(self, check_if_open=True):
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
            contract_order = self.contract_stack.get_order_with_id_from_stack(
                contract_order_id
            )
            if contract_order.fill_equals_desired_trade():
                continue
            if contract_order.is_order_controlled_by_algo():
                continue
            self.create_broker_order_for_contract_order(
                contract_order_id, check_if_open=check_if_open
            )

        return success

    def create_broker_order_for_contract_order(
        self, contract_order_id, check_if_open=True
    ):

        original_contract_order = self.contract_stack.get_order_with_id_from_stack(
            contract_order_id)
        contract_order = self.preprocess_contract_order(
            original_contract_order, check_if_open=check_if_open
        )
        if contract_order is missing_order:
            return None

        contract_order = check_and_if_required_allocate_algo_to_single_contract_order(
            self.data, contract_order)

        log = contract_order.log_with_attributes(self.log)
        log.msg("Sending order %s to algo %s" % (str(contract_order), contract_order.algo_to_use))

        algo_class_to_call = self.resolve_algo(contract_order)
        algo_instance = algo_class_to_call(self.data, contract_order)

        # THIS LINE ACTUALLY SENDS THE ORDER TO THE ALGO
        broker_order_with_controls = algo_instance.submit_trade()

        if broker_order_with_controls is missing_order:
            self.contract_stack.release_order_from_algo_control(
                contract_order_id)
            return None

        broker_order_with_controls = self.add_trade_to_database(
            broker_order_with_controls
        )
        broker_order_with_controls = algo_instance.manage_trade(
            broker_order_with_controls
        )

        result = self.post_trade_processing(broker_order_with_controls)

        return result

    def preprocess_contract_order(
            self,
            original_contract_order,
            check_if_open=True):
        data_broker = dataBroker(self.data)
        log = original_contract_order.log_with_attributes(self.log)

        # CHECK FOR LOCKS
        data_locks = dataLocks(self.data)
        instrument_locked = data_locks.is_instrument_locked(
            original_contract_order.instrument_code
        )
        if instrument_locked:
            return missing_order

        # CHECK IF OPEN
        if check_if_open:
            market_open = (
                data_broker.is_instrument_code_and_contract_date_okay_to_trade(
                    original_contract_order.instrument_code,
                    original_contract_order.contract_id,
                )
            )
            if not market_open:
                return missing_order

        # RESIZE
        contract_order = self.size_contract_order(original_contract_order)

        return contract_order

    def size_contract_order(self, original_contract_order):
        # We can deal with partially filled contract orders: that's how hard we
        # are!
        remaining_contract_order = original_contract_order.order_with_remaining()

        # Check the order doesn't breach trade limits
        contract_order_after_trade_limits = self.what_contract_trade_is_possible(
            remaining_contract_order)

        contract_order = self.liquidity_size_contract_order(
            contract_order_after_trade_limits
        )

        if contract_order is missing_order:
            return missing_order

        if contract_order.fill_equals_desired_trade():
            # Nothing left to trade
            return missing_order

        return contract_order

    def liquidity_size_contract_order(self, contract_order_after_trade_limits):
        data_broker = dataBroker(self.data)
        log = contract_order_after_trade_limits.log_with_attributes(self.log)

        # check liquidity, and if neccessary carve up order
        # Note for spread orders we check liquidity in the component markets
        liquid_qty = (
            data_broker.get_largest_offside_liquid_size_for_contract_order_by_leg(
                contract_order_after_trade_limits
            )
        )

        if liquid_qty != contract_order_after_trade_limits.trade:
            log.msg("Cut down order to size %s from %s because of liquidity" % (
                str(liquid_qty), str(contract_order_after_trade_limits.trade)))

        if liquid_qty.equals_zero():
            return missing_order

        contract_order = contract_order_after_trade_limits.replace_trade_only_use_for_unsubmitted_trades(
            liquid_qty)

        return contract_order

    def resolve_algo(self, contract_order):
        # Note we don't save the algo method, but reallocate each time
        # This is useful if trading is about to finish, because we switch to market orders
        # (assuming a bunch of limit orders haven't worked out so well)

        algo_to_use_str = contract_order.algo_to_use
        algo_method = resolve_function(algo_to_use_str)

        # This prevents another algo from trying to trade the same contract order
        # Very important to avoid multiple broker orders being issued from the
        # same contract order
        self.contract_stack.add_controlling_algo_ref(
            contract_order.order_id, algo_to_use_str
        )

        return algo_method

    def add_trade_to_database(self, broker_order_with_controls):
        broker_order = broker_order_with_controls.order

        log = broker_order.log_with_attributes(self.log)

        broker_order_id = self.broker_stack.put_order_on_stack(broker_order)
        if not isinstance(broker_order_id, int):
            # We've created a broker order but can't add it to the broker order database
            # Probably safest to leave the contract order locked otherwise there could be multiple
            #   broker orders issued and nobody wants that!
            log.critical(
                "Created a broker order %s but can't add it to the order stack!! (condition %s)" %
                (str(broker_order), str(broker_order_id)))
            return failure

        # set order_id (wouldn't have had one before)
        broker_order.order_id = broker_order_id

        # This broker order is a child of the parent contract order
        # We add 'another' child since it's valid to have multiple broker
        # orders
        contract_order_id = broker_order.parent
        self.contract_stack.add_another_child_to_order(
            contract_order_id, broker_order_id
        )

        return broker_order_with_controls

    def post_trade_processing(self, broker_order_with_controls):
        broker_order = broker_order_with_controls.order

        log = broker_order.log_with_attributes(self.log)

        # update trade limits
        self.add_trade_to_trade_limits(broker_order)

        # apply fills
        self.apply_fills_to_database(broker_order)

        # release contract order from algo
        contract_order_id = broker_order.parent
        self.contract_stack.release_order_from_algo_control(contract_order_id)

        return success

    def apply_fills_to_database(self, broker_order):
        broker_order_id = broker_order.order_id

        self.broker_stack.change_fill_quantity_for_order(
            broker_order_id,
            broker_order.fill,
            filled_price=broker_order.filled_price,
            fill_datetime=broker_order.fill_datetime,
        )

        contract_order_id = broker_order.parent

        # pass broker fills upwards
        self.apply_broker_fill_to_contract_order(contract_order_id)
