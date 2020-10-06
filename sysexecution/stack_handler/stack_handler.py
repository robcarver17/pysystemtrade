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

from sysexecution.stack_handler.spawn_children_from_instrument_orders import (
    stackHandlerForSpawning,
)
from sysexecution.stack_handler.roll_orders import stackHandlerForRolls
from sysexecution.stack_handler.create_broker_orders_from_contract_orders import (
    stackHandlerCreateBrokerOrders, )
from sysexecution.stack_handler.fills import stackHandlerForFills
from sysexecution.stack_handler.completed_orders import stackHandlerForCompletions
from sysexecution.stack_handler.cancel_and_modify import stackHandlerCancelAndModify
from sysexecution.stack_handler.checks import stackHandlerChecks


class stackHandler(
    stackHandlerForSpawning,
    stackHandlerForRolls,
    stackHandlerCreateBrokerOrders,
    stackHandlerForFills,
    stackHandlerForCompletions,
    stackHandlerCancelAndModify,
    stackHandlerChecks,
):
    def safe_stack_removal(self):
        # Safe deletion of stack
        # We do this at the end of every day as we don't like state hanging
        # around

        self.log.msg("Running safe stack removal")
        # First, cancel any partially or unfilled broker orders
        self.log.msg("Trying to cancel all broker orders")
        self.cancel_and_confirm_all_broker_orders(log_critical_on_timeout=True)

        # Next, process fills
        self.log.msg("Processing fills")
        self.process_fills_stack()

        # and then completions
        # need special flag for completions, since we also need to 'complete' partially filled orders
        # and allow empty broker orders to be marked as completed
        self.log.msg("Processing completions")
        self.handle_completed_orders(
            allow_partial_completions=True, allow_zero_completions=True
        )

    def remove_all_deactivated_orders_from_stack(self):
        # Now we can delete everything
        self.instrument_stack.remove_all_deactivated_orders_from_stack()
        self.contract_stack.remove_all_deactivated_orders_from_stack()
        self.broker_stack.remove_all_deactivated_orders_from_stack()
