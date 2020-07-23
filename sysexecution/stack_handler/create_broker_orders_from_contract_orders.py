
from syscore.objects import missing_order, success, failure, locked_order, duplicate_order, no_order_id, no_children, no_parent, missing_contract, missing_data, rolling_cant_trade, ROLL_PSEUDO_STRATEGY, missing_order, order_is_in_status_reject_modification, order_is_in_status_finished, locked_order, order_is_in_status_modified, resolve_function

from sysexecution.algos.allocate_algo_to_order import check_and_if_required_allocate_algo_to_single_contract_order

from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysproduction.data.controls import dataLocks
from sysproduction.data.broker import dataBroker

class stackHandlerCreateBrokerOrders(stackHandlerCore):


    def create_broker_orders_from_contract_orders(self, check_if_open=True):
        """
        Create broker orders from contract orders. These become child orders of the contract parent.

        Depending on the algo used, multiple broker orders might be created
        This could represent failed orders or iceberg type algos that do partial fills

        Algos are 'fire and forget' (the order is issued then the algo closes down) eg simple market order
           or 'active' (the algo controls the order until it is released)

        We need to create a new broker order and launch a new algo if:

        - the order is not completely filled AND
        - the order is not currently controlled by an algo

        :return: None
        """
        list_of_contract_order_ids = self.contract_stack.get_list_of_order_ids()
        for contract_order_id in list_of_contract_order_ids:
            contract_order = self.contract_stack.get_order_with_id_from_stack(contract_order_id)
            if contract_order.fill_equals_desired_trade():
                continue
            if contract_order.is_order_controlled_by_algo():
                continue
            self.create_broker_order_for_contract_order(contract_order_id, check_if_open=check_if_open)

        return success

    def create_broker_order_for_contract_order(self, contract_order_id, check_if_open=True):

        original_contract_order = self.contract_stack.get_order_with_id_from_stack(contract_order_id)
        log = original_contract_order.log_with_attributes(self.log)

        data_locks = dataLocks(self.data)

        instrument_locked = data_locks.is_instrument_locked(original_contract_order.instrument_code)
        if instrument_locked:
            log.msg("Instrument is locked, not spawning order")
            return None

        if check_if_open:
            data_broker = dataBroker(self.data)
            market_open = data_broker.is_instrument_code_and_contract_date_okay_to_trade(original_contract_order.instrument_code,
                                                                              original_contract_order.contract_id)
            if not market_open:
                return None

        # We can deal with partially filled contract orders: that's how hard we are!
        remaining_contract_order = original_contract_order.order_with_remaining()

        ## Check the order doesn't breach trade limits
        contract_order = self.what_contract_trade_is_possible(remaining_contract_order)

        ## Note we don't save the algo method, but reallocate each time
        ## This is useful if trading is about to finish, because we switch to market orders
        ##   (assuming a bunch of limit orders haven't worked out so well)

        contract_order = check_and_if_required_allocate_algo_to_single_contract_order(self.data, contract_order)

        algo_to_use_str = contract_order.algo_to_use
        algo_method = resolve_function(algo_to_use_str)

        ## The algo method submits an order to the broker, and returns a broker order object
        ## We then save the brokerorder in the broker stack, and add it as a child to a contract order
        ## Algos may be 'fire and forget' (a simple market order, as implemented initially) or 'active'
        ## Active algos need to keep running on another thread (need to work out how to do this)
        ## They will set the property 'reference_of_controlling_algo' in contract order
        ## Fills are picked up by another process (or if the algo is an active thing, potentially by itself)

        broker_order, reference_of_controlling_algo = algo_method(self.data, contract_order)
        if broker_order is missing_order:
            # something bad has happened and we can't submit an order to the broker
            # Nae bother, maybe try again later
            # Unlock the contract order in case we want to do this later
            self.contract_stack.release_order_from_algo_control(contract_order_id)
            return None

        ## update trade limits
        self.add_trade_to_trade_limits(broker_order)

        broker_order_id = self.broker_stack.put_order_on_stack(broker_order)
        if type(broker_order_id) is not int:
            # We've created a broker order but can't add it to the broker order database
            # Probably safest to leave the contract order locked otherwise there could be multiple
            #   broker orders issued and nobody wants that!
            log.critical("Created a broker order %s but can't add it to the order stack!! (condition %s)" %
                         (str(broker_order), str(broker_order_id)))
            return failure

        # ....create new algo lock
        # This means nobody else can try and execute this order until it is released
        # Only the algo itself can release!
        # This only applies to 'fire and forget' orders that aren't controlled by an algo

        self.contract_stack.add_controlling_algo_ref(contract_order_id, reference_of_controlling_algo)

        # This broker order is a child of the parent contract order
        # We add 'another' child since it's valid to have multiple broker orders
        self.contract_stack.add_another_child_to_order(contract_order_id, broker_order_id)

        return success

