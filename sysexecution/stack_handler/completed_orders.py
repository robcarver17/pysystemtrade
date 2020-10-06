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

from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysproduction.data.orders import dataOrders


class stackHandlerForCompletions(stackHandlerCore):
    def handle_completed_orders(
        self, allow_partial_completions=False, allow_zero_completions=False
    ):
        list_of_completed_instrument_orders = (
            self.instrument_stack.list_of_completed_orders(
                allow_partial_completions=allow_partial_completions,
                allow_zero_completions=allow_zero_completions,
            )
        )

        for instrument_order_id in list_of_completed_instrument_orders:
            self.handle_completed_instrument_order(
                instrument_order_id,
                allow_partial_completions=allow_partial_completions,
                allow_zero_completions=allow_zero_completions,
            )

    def handle_completed_instrument_order(
        self,
        instrument_order_id,
        allow_partial_completions=False,
        allow_zero_completions=False,
    ):
        # Check children all done

        (
            list_of_broker_order_id,
            list_of_contract_order_id,
        ) = self.get_all_children_and_grandchildren_for_instrument_order_id(
            instrument_order_id
        )

        completely_filled = self.confirm_all_children_and_grandchildren_are_filled(
            list_of_broker_order_id,
            list_of_contract_order_id,
            allow_partial_completions=allow_partial_completions,
            allow_zero_completions=allow_zero_completions,
        )

        if not completely_filled:
            return success

        # If we have got this far then all our children are filled, and the
        # parent is filled

        # We need to seperate out broker and contract spread orders into their individual components
        # When we do this the original orders are deactivated
        # the instrument order has it's children removed and replaced by the components of each spread order
        # the contract order
        self.split_up_spread_orders(instrument_order_id)

        # we need to do this again in case of any splits
        (
            list_of_broker_order_id,
            list_of_contract_order_id,
        ) = self.get_all_children_and_grandchildren_for_instrument_order_id(
            instrument_order_id
        )

        contract_order_list = self.contract_stack.get_list_of_orders_from_order_id_list(
            list_of_contract_order_id)
        broker_order_list = self.broker_stack.get_list_of_orders_from_order_id_list(
            list_of_broker_order_id)
        instrument_order = self.instrument_stack.get_order_with_id_from_stack(
            instrument_order_id
        )

        # Make orders inactive
        # A subsequent process will delete them
        self.deactivate_family_of_orders(
            instrument_order_id,
            list_of_contract_order_id,
            list_of_broker_order_id)

        # Update historic order database
        order_data = dataOrders(self.data)
        order_data.add_historic_orders_to_data(
            instrument_order, contract_order_list, broker_order_list
        )

        return success

    def confirm_all_children_and_grandchildren_are_filled(
        self,
        list_of_broker_order_id,
        list_of_contract_order_id,
        allow_partial_completions=False,
        allow_zero_completions=False,
    ):

        children_filled = self.check_list_of_contract_orders_complete(
            list_of_contract_order_id,
            allow_partial_completions=allow_partial_completions,
            allow_zero_completions=allow_zero_completions,
        )
        if not children_filled:
            return False

        grandchildren_filled = self.check_list_of_broker_orders_complete(
            list_of_broker_order_id,
            allow_partial_completions=allow_partial_completions,
            allow_zero_completions=allow_zero_completions,
        )

        if not grandchildren_filled:
            return False

        return True

    def check_list_of_contract_orders_complete(
        self,
        list_of_contract_order_id,
        allow_partial_completions=False,
        allow_zero_completions=False,
    ):
        for contract_order_id in list_of_contract_order_id:
            completely_filled = self.contract_stack.is_completed(
                contract_order_id,
                allow_zero_completions=allow_zero_completions,
                allow_partial_completions=allow_partial_completions,
            )
            if not completely_filled:
                # OK We can't do this unless all our children are filled
                return False

        return True

    def check_list_of_broker_orders_complete(
        self,
        list_of_broker_order_id,
        allow_partial_completions=False,
        allow_zero_completions=False,
    ):

        for broker_order_id in list_of_broker_order_id:
            completely_filled = self.broker_stack.is_completed(
                broker_order_id,
                allow_zero_completions=allow_zero_completions,
                allow_partial_completions=allow_partial_completions,
            )
            if not completely_filled:
                # OK We can't do this unless all our children are filled
                return False

        return True

    def deactivate_family_of_orders(
            self,
            instrument_order_id,
            list_of_contract_order_id,
            list_of_broker_order_id):
        # Make orders inactive
        # A subsequent process will delete them
        self.instrument_stack.deactivate_order(instrument_order_id)
        for contract_order_id in list_of_contract_order_id:
            self.contract_stack.deactivate_order(contract_order_id)

        for broker_order_id in list_of_broker_order_id:
            self.broker_stack.deactivate_order(broker_order_id)

        return success

    def split_up_spread_orders(self, instrument_order_id):
        """
        Replace spread orders with individual components

        Once finished the contract stack and broker stack will contain the original, spread-orders,
           set to zero fill,  (so they don't mess up position tables)
        plus the broken down components

        :param instrument_order_id:
        :param list_of_contract_order_id:
        :param list_of_broker_order_id:
        :return: success
        """
        original_instrument_order = self.instrument_stack.get_order_with_id_from_stack(
            instrument_order_id)
        if original_instrument_order is missing_order:
            return failure

        list_of_contract_order_id = original_instrument_order.children
        if list_of_contract_order_id is no_children:
            return failure

        new_contract_order_ids = []
        for contract_order_id in list_of_contract_order_id:
            new_contract_order_ids_for_this_contract = self.split_contract_order_id(
                contract_order_id)
            new_contract_order_ids = (
                new_contract_order_ids +
                new_contract_order_ids_for_this_contract)

        # add the new contract order ids as children for the instrument order
        for contract_order_id in new_contract_order_ids:
            self.instrument_stack.add_another_child_to_order(
                instrument_order_id, contract_order_id
            )

        return success

    def split_contract_order_id(self, contract_order_id):

        # get the original contract order
        original_contract_order = self.contract_stack.get_order_with_id_from_stack(
            contract_order_id)
        if original_contract_order is missing_order:
            return []

        # find all the relevant broker order ids
        existing_broker_ids = original_contract_order.children
        if existing_broker_ids is no_children:
            return []

        # create an empty list of new broker order ids
        new_broker_order_ids = []
        # for each broker order id
        for broker_order_id in existing_broker_ids:
            new_order_ids_for_this_broker_id = self.split_broker_order_id(
                broker_order_id
            )

            # add the new broker order ids to the list
            new_broker_order_ids = (
                new_broker_order_ids + new_order_ids_for_this_broker_id
            )

        # add the new broker order ids as children for the original contract
        # order (keep the original children)
        for new_broker_order_id in new_broker_order_ids:
            self.contract_stack.add_another_child_to_order(
                contract_order_id, new_broker_order_id
            )

        new_contract_order_ids_for_this_contract = (
            self.split_contract_order_id_once_broker_id_split(contract_order_id))

        return new_contract_order_ids_for_this_contract

    def split_contract_order_id_once_broker_id_split(self, contract_order_id):

        # reread original contract order otherwise won't include new children
        original_contract_order = self.contract_stack.get_order_with_id_from_stack(
            contract_order_id)

        if original_contract_order.calendar_spread_order:
            # Get component spread orders for the original contract order
            component_contract_orders = original_contract_order.split_spread_order()

            # set the original contract order to zero fill and dectivate
            self.contract_stack.zero_out(contract_order_id)

            # add the new contract spread orders to the database
            new_contract_order_ids_for_this_contract = (
                self.contract_stack.put_list_of_orders_on_stack(
                    component_contract_orders
                )
            )
        else:
            new_contract_order_ids_for_this_contract = []

        return new_contract_order_ids_for_this_contract

    def split_broker_order_id(self, broker_order_id):
        # get the order

        original_broker_order = self.broker_stack.get_order_with_id_from_stack(
            broker_order_id
        )
        if original_broker_order is missing_order:
            return []
        # if a spread order:
        if original_broker_order.calendar_spread_order:
            # get component spread orders
            component_broker_orders = original_broker_order.split_spread_order()

            # set the original broker order to zero fill and deactivate so we
            # don't try and fill it
            self.broker_stack.zero_out(broker_order_id)

            # add the new broker spread orders to the database
            new_order_ids_for_this_broker_id = (
                self.broker_stack.put_list_of_orders_on_stack(component_broker_orders))
        else:
            new_order_ids_for_this_broker_id = []

        return new_order_ids_for_this_broker_id
