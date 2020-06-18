"""
This piece of code processes the interface between the instrument order stack and the contract order stack and the broker order stack

Tasks it needs to accomplish:

- netting of parent orders FIX ME FUTURE
- when a new order is added to the instrument stack with no child orders, create child orders in contract order stack
- when roll status is 'force', and no parent orders, generate an 'orphan roll order (spread or outright)
- when a roll order is happening, need to lock instrument and related instruments
- when a parent order is moved to modification status, change child orders to modification status
- when all child orders are in modification complete status, change parent order to modification complete
- when a parent order and child orders are all in modification complete status, clear modification from parents and children
- when a child order has an updated fill, give the parent order a fill
  - if multiple child orders, give the parent order the fill min(child order fills)


"""

from syscore.objects import missing_order, success, failure, locked_order, duplicate_order, no_order_id, no_children, no_parent, missing_contract, missing_data, rolling_cant_trade, ROLL_PSEUDO_STRATEGY, missing_order, order_is_in_status_reject_modification, order_is_in_status_finished, locked_order, order_is_in_status_modified, resolve_function


from sysexecution.stack_handler.stack_handler_modifications import stackHandlerForModifications
from sysexecution.stack_handler.spawn_children_from_instrument_orders import stackHandlerForSpawning
from sysexecution.stack_handler.roll_orders import  stackHandlerForRolls
from sysexecution.stack_handler.create_broker_orders_from_contract_orders import stackHandlerCreateBrokerOrders
from sysexecution.stack_handler.fills import stackHandlerForFills
from sysexecution.stack_handler.completed_orders import stackHandlerForCompletions


class stackHandler(stackHandlerForModifications, stackHandlerForSpawning, stackHandlerForRolls,
                   stackHandlerCreateBrokerOrders, stackHandlerForFills,
                   stackHandlerForCompletions):

    def process_stack(self):
        """
        Run a regular sweep across the stack
        Doing various things

        :return: success
        """

        self.process_spawning_stack()
        self.process_roll_stack()
        self.process_create_broker_order_stack()
        self.process_modification_stack()
        self.process_fills_stack()
        self.process_completions_stack()

