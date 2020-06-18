from syscore.objects import missing_order, success, failure, locked_order, duplicate_order, no_order_id, no_children, no_parent, missing_contract, missing_data, rolling_cant_trade, ROLL_PSEUDO_STRATEGY, missing_order, order_is_in_status_reject_modification, order_is_in_status_finished, locked_order, order_is_in_status_modified, resolve_function, ROLL_PSEUDO_STRATEGY

from sysexecution.contract_orders import log_attributes_from_contract_order

from sysexecution.contract_orders import contractOrder
from sysexecution.instrument_orders import instrumentOrder
from sysexecution.algos.allocate_algo_to_order import allocate_algo_to_list_of_contract_orders

from sysproduction.data.positions import diagPositions
from sysproduction.data.contracts import diagContracts
from sysproduction.data.prices import diagPrices

from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore

class stackHandlerForRolls(stackHandlerCore):

    def process_roll_stack(self):
        """
        Run a regular sweep across the stack
        Doing various things

        :return: success
        """

        self.generate_force_roll_orders()

    def generate_force_roll_orders(self):
        diag_positions = diagPositions(self.data)
        list_of_instruments = diag_positions.get_list_of_instruments_with_any_position()
        for instrument_code in list_of_instruments:
            self.generate_force_roll_orders_for_instrument(instrument_code)

    def generate_force_roll_orders_for_instrument(self, instrument_code):
        log = self.data.log.setup(instrument_code = instrument_code, strategy_name = ROLL_PSEUDO_STRATEGY)

        instrument_order, contract_orders = create_force_roll_orders(self.data, instrument_code)
        # Create a pseudo instrument order and a set of contract orders
        # This will also prevent trying to generate more than one set of roll orders

        if len(contract_orders)==0 or instrument_order is missing_order:
            # No orders
            return None

        # Do as a transaction: if everything doesn't go to plan can roll back
        instrument_order.lock_order()
        instrument_order_id = self.instrument_stack.put_order_on_stack(instrument_order, allow_zero_orders=True)

        if type(instrument_order_id) is not int:
            if instrument_order_id is duplicate_order:
                # Probably already done this
                return success
            else:
                log.msg("Couldn't put roll order %s on instrument order stack error %s" % (str(instrument_order),
                                                                                           str(instrument_order_id)))
            return failure

        for child_order in contract_orders:
            child_order.parent = instrument_order_id

        # Do as a transaction: if everything doesn't go to plan can roll back
        # if this try fails we will roll back the instrument commit
        try:
            log = log.setup(instrument_order_id= instrument_order_id)

            log.msg("List of roll contract orders spawned %s" % str(contract_orders))
            list_of_child_order_ids = self.contract_stack.put_list_of_orders_on_stack(contract_orders, unlock_when_finished=False)

            if list_of_child_order_ids is failure:
                log.msg("Failed to add roll contract orders to stack %s" % (str(contract_orders)))
                list_of_child_order_ids = []
                raise Exception

            for roll_order, order_id in zip(contract_orders, list_of_child_order_ids):
                child_log = log_attributes_from_contract_order(log, roll_order)
                child_log.msg("Put roll order %s on contract_stack with ID %d from parent order %s" % (str(roll_order),
                                                                                              order_id,
                                                                                              str(instrument_order)))

            self.instrument_stack._unlock_order_on_stack(instrument_order_id)
            result = self.instrument_stack.add_children_to_order(instrument_order_id, list_of_child_order_ids)
            if result is not success:
                log.msg("Error %s when adding children to instrument roll order %s" % (str(result), str(instrument_order)))
                raise Exception

            self.contract_stack.unlock_list_of_orders(list_of_child_order_ids)

        except:
            ## Roll back instrument order
            self.instrument_stack._unlock_order_on_stack(instrument_order_id)
            self.instrument_stack.deactivate_order(instrument_order_id)
            self.instrument_stack.remove_order_with_id_from_stack(instrument_order_id)

            # If any children, roll them back also
            if len(list_of_child_order_ids)>0:
                self.contract_stack.rollback_list_of_orders_on_stack(list_of_child_order_ids)

            return failure

        return success



def create_force_roll_orders(data, instrument_code):
    """

    :param data:
    :param instrument_code:
    :return: tuple; instrument_order (or missing_order), contract_orders
    """
    diag_positions = diagPositions(data)
    roll_state = diag_positions.get_roll_state(instrument_code)
    if roll_state not in ['Force', 'Force_Outright']:
        return missing_order, []

    strategy = ROLL_PSEUDO_STRATEGY
    trade = 0
    instrument_order = instrumentOrder(strategy, instrument_code, trade, roll_order=True, order_type="Zero-roll-order")

    diag_contracts = diagContracts(data)
    priced_contract_id = diag_contracts.get_priced_contract_id(instrument_code)
    forward_contract_id = diag_contracts.get_forward_contract_id(instrument_code)
    position_in_priced = diag_positions.get_position_for_instrument_and_contract_date(instrument_code, priced_contract_id)

    if roll_state=='Force_Outright':
        contract_orders = create_contract_orders_outright(data,  instrument_code, priced_contract_id, forward_contract_id, position_in_priced)
    elif roll_state=='Force':
        contract_orders = create_contract_orders_spread(data,  instrument_code, priced_contract_id, forward_contract_id, position_in_priced)
    else:
        raise  Exception("Roll state %s not recognised" % roll_state)

    contract_orders = allocate_algo_to_list_of_contract_orders(data, instrument_order, contract_orders)

    return instrument_order, contract_orders

def create_contract_orders_outright(data, instrument_code,
                                    priced_contract_id, forward_contract_id, position_in_priced):
    diag_prices = diagPrices(data)
    reference_price_priced_contract, reference_price_forward_contract = \
        tuple(diag_prices.get_last_matched_prices_for_contract_list(
            instrument_code, [priced_contract_id, forward_contract_id]))
    strategy = ROLL_PSEUDO_STRATEGY
    first_order = contractOrder(strategy, instrument_code, priced_contract_id, -position_in_priced,
                                reference_price=reference_price_priced_contract, roll_order=True,
                                inter_spread_order=True)
    second_order = contractOrder(strategy, instrument_code, forward_contract_id, position_in_priced,
                                 reference_price=reference_price_forward_contract, roll_order=True,
                                 inter_spread_order=True)

    return [first_order, second_order]

def create_contract_orders_spread(data, instrument_code,
                                  priced_contract_id, forward_contract_id, position_in_priced):

    diag_prices = diagPrices(data)
    reference_price_priced_contract, reference_price_forward_contract = \
        tuple(diag_prices.get_last_matched_prices_for_contract_list(
            instrument_code, [priced_contract_id, forward_contract_id]))

    strategy = ROLL_PSEUDO_STRATEGY
    contract_id_list = [priced_contract_id, forward_contract_id]
    trade_list = [-position_in_priced, position_in_priced]
    spread_reference_price = reference_price_priced_contract - reference_price_forward_contract

    spread_order = contractOrder(strategy, instrument_code, contract_id_list, trade_list,
                                reference_price=spread_reference_price, roll_order=True)

    return [spread_order]
