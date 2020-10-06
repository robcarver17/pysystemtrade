from syscore.objects import failure, success, missing_order
from sysexecution.stack_handler.completed_orders import stackHandlerForCompletions
from sysexecution.stack_handler.fills import stackHandlerForFills
from sysexecution.instrument_orders import instrumentOrder
from sysexecution.contract_orders import contractOrder


class stackHandlerCreateBalanceTrades(
        stackHandlerForCompletions,
        stackHandlerForFills):
    def create_balance_trade(self, broker_order):
        log = broker_order.log_with_attributes(self.log)

        contract_order = create_balance_contract_order_from_broker_order(
            broker_order)
        instrument_order = create_balance_instrument_order_from_contract_order(
            contract_order
        )

        log.msg("Putting balancing trades on stacks")

        (
            result,
            instrument_order_id,
            contract_order_id,
            broker_order_id,
        ) = self.put_balance_trades_on_stack(
            instrument_order, contract_order, broker_order
        )

        if result is failure:
            log.error("Something went wrong, rolling back")
            self.rollback_balance_trades(
                instrument_order_id, contract_order_id, broker_order_id
            )
            return failure

        contract_order.order_id = contract_order_id
        instrument_order.order_id = instrument_order_id

        log.msg("Updating positions")
        self.apply_position_change_to_contracts(
            contract_order, contract_order.fill, apply_entire_trade=True
        )
        self.apply_position_change_to_instrument(
            instrument_order, instrument_order.fill, apply_entire_trade=True
        )

        log.msg("Marking balancing trades as completed and historic order data")
        self.handle_completed_instrument_order(instrument_order_id)

        return success

    def put_balance_trades_on_stack(
        self, instrument_order, contract_order, broker_order
    ):
        log = instrument_order.log_with_attributes(self.log)
        log.msg("Putting balancing trades on stacks")
        instrument_order_id = self.instrument_stack.put_manual_order_on_stack(
            instrument_order
        )

        if not isinstance(instrument_order_id, int):
            log.error(
                "Couldn't add balancing instrument trade error condition %s"
                % str(instrument_order_id)
            )
            return failure, missing_order, missing_order, missing_order

        contract_order.parent = instrument_order_id
        contract_order_id = self.contract_stack.put_order_on_stack(
            contract_order)
        if not isinstance(contract_order_id, int):
            log.error(
                "Couldn't add balancing contract trade error condition %s"
                % str(contract_order_id)
            )
            return failure, instrument_order_id, missing_order, missing_order

        result = self.instrument_stack.add_children_to_order(
            instrument_order_id, [contract_order_id]
        )
        if result is not success:
            log.error("Couldn't add children to instrument order")
            return failure, instrument_order_id, contract_order_id, missing_order

        broker_order.parent = contract_order_id
        broker_order_id = self.broker_stack.put_order_on_stack(broker_order)
        if not isinstance(broker_order_id, int):
            log.error(
                "Couldn't add balancing broker trade error condition %s"
                % str(broker_order_id)
            )
            return failure, instrument_order_id, contract_order_id, missing_order

        result = self.contract_stack.add_children_to_order(
            contract_order_id, [broker_order_id]
        )
        if result is not success:
            log.error("Couldn't add children to contract order")
            return failure, instrument_order_id, contract_order_id, broker_order_id

        log.msg("All balancing trades added to stacks")

        return success, instrument_order_id, contract_order_id, broker_order_id

    def rollback_balance_trades(
        self, instrument_order_id, contract_order_id, broker_order_id
    ):

        if instrument_order_id is not missing_order:
            self.instrument_stack.remove_order_with_id_from_stack(
                instrument_order_id)
        if contract_order_id is not missing_order:
            self.contract_stack.remove_order_with_id_from_stack(
                contract_order_id)
        if broker_order_id is not missing_order:
            self.broker_stack.remove_order_with_id_from_stack(broker_order_id)

        return success

    def create_balance_instrument_trade(self, instrument_order):
        log = instrument_order.log_with_attributes(self.log)
        log.msg("Putting balancing on stacks")
        instrument_order_id = self.instrument_stack.put_manual_order_on_stack(
            instrument_order
        )

        instrument_order.order_id = instrument_order_id

        log.msg(
            "Marking balancing trades as completed and updating positions and historic order data"
        )
        self.apply_position_change_to_instrument(
            instrument_order, instrument_order.fill, apply_entire_trade=True
        )
        self.handle_completed_instrument_order(instrument_order_id)

        return success


def create_balance_contract_order_from_broker_order(broker_order):
    contract_order = contractOrder(
        broker_order.strategy_name,
        broker_order.instrument_code,
        broker_order.contract_id,
        broker_order.trade,
        fill=broker_order.fill,
        algo_to_use=broker_order.algo_used,
        filled_price=broker_order.filled_price,
        fill_datetime=broker_order.fill_datetime,
        manual_fill=True,
        manual_trade=True,
        active=False,
    )

    return contract_order


def create_balance_instrument_order_from_contract_order(contract_order):
    instrument_order = instrumentOrder(
        contract_order.strategy_name,
        contract_order.instrument_code,
        contract_order.trade[0],
        fill=contract_order.fill[0],
        filled_price=contract_order.filled_price,
        fill_datetime=contract_order.fill_datetime,
        manual_trade=True,
        active=False,
    )
    return instrument_order
