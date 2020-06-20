
from syscore.objects import missing_order, success, failure, locked_order, duplicate_order, no_order_id, no_children, no_parent, missing_contract, missing_data, rolling_cant_trade, ROLL_PSEUDO_STRATEGY, missing_order, order_is_in_status_reject_modification, order_is_in_status_finished, locked_order, order_is_in_status_modified, resolve_function

from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysproduction.data.positions import updatePositions
from sysproduction.data.orders import dataOrders

class stackHandlerForCompletions(stackHandlerCore):

    def process_completions_stack(self):
        """
        Run a regular sweep across the stack
        Doing various things

        :return: success
        """

        self.handle_completed_orders()



    def handle_completed_orders(self):
        list_of_instrument_order_ids = self.instrument_stack.get_list_of_order_ids()
        for instrument_order_id in list_of_instrument_order_ids:
            if self.instrument_stack.is_completed(instrument_order_id):
                self.handle_completed_instrument_order(instrument_order_id)

    def handle_completed_instrument_order(self, instrument_order_id):
        ## Check children all done
        instrument_order = self.instrument_stack.get_order_with_id_from_stack(instrument_order_id)

        list_of_broker_order_id, list_of_contract_order_id = self.\
            get_all_children_and_grandchildren_for_instrument_order_id(instrument_order_id)

        completely_filled = self.\
            confirm_all_children_and_grandchildren_are_filled(list_of_broker_order_id, list_of_contract_order_id)

        if not completely_filled:
            return success

        # If we have got this far then all our children are filled, and the parent is filled
        contract_order_list = self.contract_stack.get_list_of_orders_from_order_id_list(list_of_contract_order_id)
        broker_order_list = self.broker_stack.get_list_of_orders_from_order_id_list(list_of_broker_order_id)

        # update positions
        position_updater = updatePositions(self.data)
        position_updater.update_positions_with_instrument_and_contract_orders(instrument_order, contract_order_list)

        # Update historic order database
        order_data = dataOrders(self.data)
        order_data.add_historic_orders_to_data(instrument_order, contract_order_list, broker_order_list)

        # Make orders inactive
        # A subsequent process will delete them
        self.deactivate_family_of_orders(instrument_order_id, list_of_contract_order_id, list_of_broker_order_id)

        return success
