from syscore.objects import (
    fill_exceeds_trade,
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

from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysexecution.base_orders import listOfFillPrice
from sysproduction.data.broker import dataBroker
from sysproduction.data.positions import updatePositions


class stackHandlerForFills(stackHandlerCore):
    def process_fills_stack(self):
        """
        Run a regular sweep across the stack
        Doing various things

        :return: success
        """

        self.pass_fills_from_broker_to_broker_stack()
        self.pass_fills_from_broker_up_to_contract()
        self.pass_fills_from_contract_up_to_instrument()

    def pass_fills_from_broker_to_broker_stack(self):
        list_of_broker_order_ids = self.broker_stack.get_list_of_order_ids()
        for broker_order_id in list_of_broker_order_ids:
            self.apply_broker_fill_to_broker_stack(broker_order_id)

    def apply_broker_fill_to_broker_stack(self, broker_order_id):

        db_broker_order = self.broker_stack.get_order_with_id_from_stack(
            broker_order_id
        )
        if db_broker_order is missing_order:
            return failure

        log = db_broker_order.log_with_attributes(self.log)

        if db_broker_order.fill_equals_desired_trade():
            # No point
            # We don't log or we'd be spamming like crazy
            return success

        data_broker = dataBroker(self.data)
        matched_broker_order = data_broker.match_db_broker_order_to_order_from_brokers(
            db_broker_order)

        if matched_broker_order is missing_order:
            log.warn(
                "Order %s does not match any broker orders" %
                db_broker_order)
            return failure

        result = self.broker_stack.add_execution_details_from_matched_broker_order(
            broker_order_id, matched_broker_order)

        if result is fill_exceeds_trade:
            self.log.warn(
                "Fill for %s exceeds trade for %s, ignoring... (hopefully will go away)" %
                (db_broker_order, matched_broker_order))

        return result

    def pass_fills_from_broker_up_to_contract(self):
        list_of_contract_order_ids = self.contract_stack.get_list_of_order_ids()
        for contract_order_id in list_of_contract_order_ids:
            # this function is in 'core' since it's used elsewhere
            self.apply_broker_fill_to_contract_order(contract_order_id)

    def pass_fills_from_contract_up_to_instrument(self):
        list_of_child_order_ids = self.contract_stack.get_list_of_order_ids()
        for contract_order_id in list_of_child_order_ids:
            self.apply_contract_fill_to_instrument_order(contract_order_id)

    def apply_contract_fill_to_instrument_order(self, contract_order_id):
        contract_order = self.contract_stack.get_order_with_id_from_stack(
            contract_order_id
        )
        log = contract_order.log_with_attributes(self.log)

        if contract_order.fill_equals_zero():
            # Nothing to do here
            return success

        contract_parent_id = contract_order.parent
        if contract_parent_id is no_parent:
            log.error(
                "No parent for contract order %s %d"
                % (str(contract_order), contract_order_id)
            )
            return failure

        instrument_order = self.instrument_stack.get_order_with_id_from_stack(
            contract_parent_id
        )
        list_of_contract_order_ids = instrument_order.children

        # This will be a list...

        if len(list_of_contract_order_ids) == 1:
            # easy, only one child
            result = self.apply_contract_fill_to_parent_order_single_child(
                contract_order, instrument_order
            )
        else:
            result = self.apply_contract_fill_to_parent_order_multiple_children(
                list_of_contract_order_ids, instrument_order)

        return result

    def apply_contract_fill_to_parent_order_single_child(
        self, contract_order, instrument_order
    ):
        log = contract_order.log_with_attributes(self.log)

        fill_for_contract = contract_order.fill
        filled_price = contract_order.filled_price
        fill_datetime = contract_order.fill_datetime
        if len(fill_for_contract) == 1:
            # Not a spread order, trivial
            result = self.fill_for_instrument_in_database(
                instrument_order, fill_for_contract, filled_price, fill_datetime)

        else:
            # Spread order: intra-market
            # Instrument order quantity is either zero (for a roll) or non zero
            # (for a spread)
            if instrument_order.is_zero_trade():
                # A roll; meaningless to do this
                result = success
            else:
                # A proper spread order with non zero legs
                log.critical(
                    "Can't handle non-flat intra-market spread orders! Instrument order %s %s" %
                    (str(instrument_order), str(
                        instrument_order.order_id)))
                result = failure

        return result

    def apply_contract_fill_to_parent_order_multiple_children(
        self, list_of_contract_order_ids, instrument_order
    ):
        log = instrument_order.log_with_attributes(self.log)
        if instrument_order.is_zero_trade():
            # An inter-market flat spread
            # Meaningless to do this
            result = success
            return result

        distributed_order = self.check_to_see_if_distributed_instrument_order(
            list_of_contract_order_ids, instrument_order
        )

        if distributed_order:
            # a distributed order, all orders have the same sign as the
            # instrument order
            result = self.apply_contract_fill_to_parent_order_distributed_children(
                list_of_contract_order_ids, instrument_order)
            return result

        # A proper spread trade across markets
        log.critical(
            "Can't handle inter-market spread orders yet! Instrument order %s %s" %
            (str(instrument_order), str(
                instrument_order.order_id)))
        return failure

    def check_to_see_if_distributed_instrument_order(
        self, list_of_contract_order_ids, instrument_order
    ):
        # A distributed instrument order is like this: buy 2 EDOLLAR instrument order
        # split into buy 1 202306, buy 1 203209

        contract_orders = [
            self.contract_stack.get_order_with_id_from_stack(contract_id)
            for contract_id in list_of_contract_order_ids
        ]

        trade_instrument_order = instrument_order.trade
        trade_contract_orders = [order.trade for order in contract_orders]

        instrument_code_from_instrument_order = instrument_order.instrument_code
        matching_instruments = [
            order.instrument_code == instrument_code_from_instrument_order
            for order in contract_orders
        ]
        all_instruments_match = all(matching_instruments)

        matching_signs = [trade.sign_equal(
            trade_instrument_order) for trade in trade_contract_orders]
        all_signs_match = all(matching_signs)

        sum_contract_orders = sum(trade_contract_orders)
        sums_match = sum_contract_orders == trade_instrument_order

        if all_signs_match and sums_match and all_instruments_match:
            return True
        else:
            return False

    def apply_contract_fill_to_parent_order_distributed_children(
        self, list_of_contract_order_ids, instrument_order
    ):
        # A distributed instrument order is like this: buy 2 EDOLLAR instrument order
        # split into buy 1 202306, buy 1 203209

        ##
        log = instrument_order.log_with_attributes(self.log)

        contract_orders = [
            self.contract_stack.get_order_with_id_from_stack(contract_id)
            for contract_id in list_of_contract_order_ids
        ]

        # We apply: total quantity, average price, highest datetime

        list_of_filled_qty = [order.fill for order in contract_orders]
        list_of_filled_price = listOfFillPrice(
            [order.filled_price for order in contract_orders]
        )
        list_of_filled_datetime = [
            order.fill_datetime for order in contract_orders]

        final_fill_datetime = max(list_of_filled_datetime)
        total_filled_qty = sum(list_of_filled_qty)
        average_fill_price = list_of_filled_price.average_fill_price()

        result = self.fill_for_instrument_in_database(
            instrument_order, total_filled_qty, average_fill_price, final_fill_datetime)

        return result

    def fill_for_instrument_in_database(
        self, instrument_order, fill_qty, fill_price, fill_datetime
    ):

        # if fill has changed then update positions
        self.apply_position_change_to_instrument(instrument_order, fill_qty)

        result = self.instrument_stack.change_fill_quantity_for_order(
            instrument_order.order_id,
            fill_qty,
            filled_price=fill_price,
            fill_datetime=fill_datetime,
        )

        return result

    def apply_position_change_to_instrument(
        self, instrument_order, total_filled_qty, apply_entire_trade=False
    ):
        current_fill = instrument_order.fill

        if apply_entire_trade:
            new_fill = current_fill
        else:
            if total_filled_qty == current_fill:
                # no change needed here
                return success

            new_fill = total_filled_qty - current_fill

        position_updater = updatePositions(self.data)
        result = position_updater.update_strategy_position_table_with_instrument_order(
            instrument_order, new_fill)

        return result
