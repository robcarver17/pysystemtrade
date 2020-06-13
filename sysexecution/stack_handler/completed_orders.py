
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
        list_of_completed_instrument_orders = self.instrument_stack.list_of_completed_orders()
        for instrument_order_id in list_of_completed_instrument_orders:
            self.handle_completed_instrument_order(instrument_order_id)

    def handle_completed_instrument_order(self, instrument_order_id):
        ## Check children all done
        instrument_order = self.instrument_stack.get_order_with_id_from_stack(instrument_order_id)
        list_of_contract_order_id = instrument_order.children
        if list_of_contract_order_id is no_children:
            list_of_contract_order_id = []

        list_of_broker_order_id = []
        list_of_contract_orders = []

        for contract_order_id in list_of_contract_order_id:
            contract_order = self.contract_stack.get_order_with_id_from_stack(contract_order_id)
            list_of_contract_orders.append(self.contract_stack.get_order_with_id_from_stack(contract_order_id))

            broker_order_children = contract_order.children
            if broker_order_children is not no_children:
                list_of_broker_order_id = list_of_broker_order_id+broker_order_children

        for contract_order_id in list_of_contract_order_id:
            completely_filled = self.contract_stack.is_completed(contract_order_id)
            if not completely_filled:
                ## OK We can't do this unless all our children are filled
                return success

        for broker_order_id in list_of_broker_order_id:
            completely_filled = self.broker_stack.is_completed(broker_order_id)
            if not completely_filled:
                ## OK We can't do this unless all our children are filled
                return success


        # If we have got this far then all our children are filled, and the parent is filled
        position_updater = updatePositions(self.data)
        # Update strategy position table
        position_updater.update_strategy_position_table_with_instrument_order(instrument_order)

        # Update contract position table
        for contract_order in list_of_contract_orders:
            position_updater.update_contract_position_table_with_contract_order(contract_order)

        order_data = dataOrders(self.data)
        # Update historic order database
        order_data.add_historic_instrument_order_to_data(instrument_order)
        for contract_order in list_of_contract_orders:
            order_data.add_historic_contract_order_to_data(contract_order)

        for broker_order_id in list_of_broker_order_id:
            broker_order = self.broker_stack.get_order_with_id_from_stack(broker_order_id)
            order_data.add_historic_broker_order_to_data(broker_order)


        # Make orders inactive
        # A subsequent process will delete them
        self.instrument_stack.deactivate_order(instrument_order_id)
        for contract_order_id in list_of_contract_order_id:
            self.contract_stack.deactivate_order(contract_order_id)

        for broker_order_id in list_of_broker_order_id:
            self.broker_stack.deactivate_order(broker_order_id)

        return success
