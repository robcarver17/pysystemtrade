from sysexecution.stack_handler.spawn_children_from_instrument_orders import (
    stackHandlerForSpawning,
)
from sysexecution.stack_handler.roll_orders import stackHandlerForRolls
from sysexecution.stack_handler.create_broker_orders_from_contract_orders import (
    stackHandlerCreateBrokerOrders,
)
from sysexecution.stack_handler.cancel_and_modify import stackHandlerCancelAndModify
from sysexecution.stack_handler.checks import stackHandlerChecks
from sysexecution.stack_handler.additional_sampling import (
    stackHandlerAdditionalSampling,
)


class stackHandler(
    stackHandlerForSpawning,
    stackHandlerForRolls,
    stackHandlerCreateBrokerOrders,
    stackHandlerCancelAndModify,
    stackHandlerChecks,
    stackHandlerAdditionalSampling,
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

        self.remove_all_deactivated_orders_from_stack()

    def remove_all_deactivated_orders_from_stack(self):
        # Now we can delete everything
        self.instrument_stack.remove_all_deactivated_orders_from_stack()
        self.contract_stack.remove_all_deactivated_orders_from_stack()
        self.broker_stack.remove_all_deactivated_orders_from_stack()
