from sysexecution.order_stacks.order_stack import failureWithRollback
from sysexecution.orders.named_order_objects import missing_order
from sysexecution.stack_handler.fills import stackHandlerForFills
from sysexecution.orders.instrument_orders import instrumentOrder
from sysexecution.orders.contract_orders import contractOrder
from sysexecution.orders.contract_orders import (
    balance_order_type as balance_order_type_for_contract_orders,
)
from sysexecution.orders.instrument_orders import (
    balance_order_type as balance_order_type_for_instrument_orders,
)
from sysexecution.orders.broker_orders import brokerOrder


class stackHandlerCreateBalanceTrades(stackHandlerForFills):
    def create_balance_trade(self, broker_order: brokerOrder):
        log = broker_order.log_with_attributes(self.log)

        contract_order = create_balance_contract_order_from_broker_order(broker_order)
        instrument_order = create_balance_instrument_order_from_contract_order(
            contract_order
        )

        log.debug("Putting balancing trades on stacks")

        try:
            self.put_balance_trades_on_stack(
                instrument_order, contract_order, broker_order
            )
        except failureWithRollback:
            return None

        log.debug("Updating positions")
        self.apply_position_change_to_stored_contract_positions(
            contract_order, contract_order.fill, apply_entire_trade=True
        )
        self.apply_position_change_to_instrument(
            instrument_order, instrument_order.fill, apply_entire_trade=True
        )

        log.debug("Marking balancing trades as completed and historic order data")
        self.handle_completed_instrument_order(
            instrument_order.order_id, treat_inactive_as_complete=True
        )

    def put_balance_trades_on_stack(
        self,
        instrument_order: instrumentOrder,
        contract_order: contractOrder,
        broker_order: brokerOrder,
    ):
        log = instrument_order.log_with_attributes(self.log)
        log.debug("Putting balancing trades on stacks")

        try:
            instrument_order_id = (
                self.instrument_stack.put_manual_order_on_stack_and_return_order_id(
                    instrument_order
                )
            )
        except Exception as e:
            log.error(
                "Couldn't add balancing instrument trade error condition %s" % str(e)
            )
            log.error("Nothing to roll back")
            raise failureWithRollback from e

        try:
            contract_order.parent = instrument_order_id
            contract_order_id = self.contract_stack.put_order_on_stack(contract_order)
        except Exception as e:
            log.error(
                "Couldn't add balancing contract trade error condition %s " % str(e)
            )
            log.error("Rolling back")
            self.rollback_balance_trades(
                instrument_order_id, missing_order, missing_order
            )
            raise failureWithRollback from e

        try:
            self.instrument_stack.add_children_to_order_without_existing_children(
                instrument_order_id, [contract_order_id]
            )
        except Exception as e:

            log.error("Couldn't add children to instrument order error %s" % str(e))
            log.error("Rolling back")
            self.rollback_balance_trades(
                instrument_order_id, contract_order_id, missing_order
            )
            raise failureWithRollback from e

        broker_order.parent = contract_order_id
        try:
            broker_order_id = self.broker_stack.put_order_on_stack(broker_order)
        except Exception as e:
            log.error("Couldn't add balancing broker trade error condition %s" % str(e))
            log.error("Rolling back")
            self.rollback_balance_trades(
                instrument_order_id, contract_order_id, missing_order
            )
            raise failureWithRollback from e

        try:
            self.contract_stack.add_children_to_order_without_existing_children(
                contract_order_id, [broker_order_id]
            )
        except Exception as e:
            log.error("Couldn't add children to contract order exception %s" % str(e))
            log.error("Rolling back")
            self.rollback_balance_trades(
                instrument_order_id, contract_order_id, broker_order_id
            )
            raise failureWithRollback from e

        contract_order.order_id = contract_order_id
        instrument_order.order_id = instrument_order_id

        log.debug("All balancing trades added to stacks")

    def rollback_balance_trades(
        self, instrument_order_id: int, contract_order_id: int, broker_order_id: int
    ):

        if instrument_order_id is not missing_order:
            self.instrument_stack.remove_order_with_id_from_stack(instrument_order_id)
        if contract_order_id is not missing_order:
            self.contract_stack.remove_order_with_id_from_stack(contract_order_id)
        if broker_order_id is not missing_order:
            self.broker_stack.remove_order_with_id_from_stack(broker_order_id)

    def create_balance_instrument_trade(self, instrument_order: instrumentOrder):
        log = instrument_order.log_with_attributes(self.log)
        log.debug("Putting balancing order on instrument stack")
        instrument_order_id = (
            self.instrument_stack.put_manual_order_on_stack_and_return_order_id(
                instrument_order
            )
        )

        instrument_order.order_id = instrument_order_id

        log.debug(
            "Marking balancing trades as completed and updating positions and historic order data"
        )
        self.apply_position_change_to_instrument(
            instrument_order, instrument_order.fill, apply_entire_trade=True
        )
        self.handle_completed_instrument_order(instrument_order_id)


def create_balance_contract_order_from_broker_order(broker_order: brokerOrder):
    contract_order = contractOrder(
        broker_order.strategy_name,
        broker_order.instrument_code,
        broker_order.contract_date_key,
        broker_order.trade,
        fill=broker_order.fill,
        algo_to_use=broker_order.algo_used,
        filled_price=broker_order.filled_price,
        fill_datetime=broker_order.fill_datetime,
        manual_fill=True,
        manual_trade=True,
        active=False,
        order_type=balance_order_type_for_contract_orders,
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
        order_type=balance_order_type_for_instrument_orders,
    )
    return instrument_order
