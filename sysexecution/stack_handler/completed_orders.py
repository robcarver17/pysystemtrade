
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



    def handle_completed_orders(self, allow_partial_completions = False,
                                allow_zero_completions = False):
        list_of_completed_instrument_orders = \
            self.instrument_stack.list_of_completed_orders(allow_partial_completions = allow_partial_completions,
                                                           allow_zero_completions = allow_zero_completions)
        for instrument_order_id in list_of_completed_instrument_orders:
            self.handle_completed_instrument_order(instrument_order_id,
                                                   allow_partial_completions = allow_partial_completions,
                                                   allow_zero_completions = allow_zero_completions)


    def handle_completed_instrument_order(self, instrument_order_id,
                                          allow_partial_completions = False, allow_zero_completions = False):
        ## Check children all done
        instrument_order = self.instrument_stack.get_order_with_id_from_stack(instrument_order_id)

        list_of_broker_order_id, list_of_contract_order_id = self.\
            get_all_children_and_grandchildren_for_instrument_order_id(instrument_order_id)

        completely_filled = self.\
            confirm_all_children_and_grandchildren_are_filled(list_of_broker_order_id, list_of_contract_order_id,
                                                              allow_partial_completions=allow_partial_completions,
                                                              allow_zero_completions = allow_zero_completions)

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

    def confirm_all_children_and_grandchildren_are_filled(self, list_of_broker_order_id, list_of_contract_order_id,
                                                          allow_partial_completions = False,
                                                          allow_zero_completions = False):

        children_filled = self.check_list_of_contract_orders_complete(list_of_contract_order_id,
                                                                      allow_partial_completions=allow_partial_completions,
                                                                      allow_zero_completions = allow_zero_completions)
        if not children_filled:
            return False

        grandchildren_filled = self.check_list_of_broker_orders_complete(list_of_broker_order_id,
                                                                         allow_partial_completions=allow_partial_completions,
                                                                         allow_zero_completions = allow_zero_completions)

        if not grandchildren_filled:
            return False

        return True

    def check_list_of_contract_orders_complete(self, list_of_contract_order_id, allow_partial_completions = False,
                                               allow_zero_completions = False):
        for contract_order_id in list_of_contract_order_id:
            completely_filled = self.contract_stack.is_completed(contract_order_id,
                                                                 allow_zero_completions = allow_zero_completions,
                                                                 allow_partial_completions=allow_partial_completions)
            if not completely_filled:
                ## OK We can't do this unless all our children are filled
                return False

        return True

    def check_list_of_broker_orders_complete(self, list_of_broker_order_id, allow_partial_completions = False,
                                             allow_zero_completions = False):

        for broker_order_id in list_of_broker_order_id:
            completely_filled = self.broker_stack.is_completed(broker_order_id,
                                                               allow_zero_completions = allow_zero_completions,
                                                               allow_partial_completions=allow_partial_completions)
            if not completely_filled:
                ## OK We can't do this unless all our children are filled
                return False

        return True

    def deactivate_family_of_orders(self, instrument_order_id, list_of_contract_order_id, list_of_broker_order_id):
        # Make orders inactive
        # A subsequent process will delete them
        self.instrument_stack.deactivate_order(instrument_order_id)
        for contract_order_id in list_of_contract_order_id:
            self.contract_stack.deactivate_order(contract_order_id)

        for broker_order_id in list_of_broker_order_id:
            self.broker_stack.deactivate_order(broker_order_id)

        return success