from syscore.objects import missing_order, ROLL_PSEUDO_STRATEGY

from sysexecution.contract_orders import contractOrder
from sysexecution.instrument_orders import instrumentOrder
from sysexecution.algos.allocate_algo_to_order import (
    allocate_algo_to_list_of_contract_orders,
)

from sysproduction.data.positions import diagPositions
from sysproduction.data.contracts import diagContracts
from sysproduction.data.prices import diagPrices

from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore


class stackHandlerForRolls(stackHandlerCore):
    def generate_force_roll_orders(self):
        diag_positions = diagPositions(self.data)
        list_of_instruments = diag_positions.get_list_of_instruments_with_current_positions()
        for instrument_code in list_of_instruments:
            self.generate_force_roll_orders_for_instrument(instrument_code)

    def generate_force_roll_orders_for_instrument(self, instrument_code):
        log = self.data.log.setup(
            instrument_code=instrument_code, strategy_name=ROLL_PSEUDO_STRATEGY
        )
        roll_required = self.check_roll_required(instrument_code)
        if not roll_required:
            return None

        instrument_order, contract_orders = create_force_roll_orders(
            self.data, instrument_code
        )
        # Create a pseudo instrument order and a set of contract orders
        # This will also prevent trying to generate more than one set of roll
        # orders

        if len(contract_orders) == 0 or instrument_order is missing_order:
            # No orders
            return None

        result = self.add_parent_and_list_of_child_orders_to_stack(
            self.instrument_stack,
            self.contract_stack,
            instrument_order,
            contract_orders,
        )

        return result

    def check_roll_required(self, instrument_code):
        order_already_on_stack = self.check_if_roll_order_already_on_stack(
            instrument_code
        )
        forced_roll_required = self.check_if_forced_roll_required(
            instrument_code)

        if order_already_on_stack:
            return False

        if not forced_roll_required:
            return False

        return True

    def check_if_roll_order_already_on_stack(self, instrument_code):
        result = self.instrument_stack.does_strategy_and_instrument_already_have_order_on_stack(
            ROLL_PSEUDO_STRATEGY, instrument_code)

        return result

    def check_if_forced_roll_required(self, instrument_code):
        diag_positions = diagPositions(self.data)
        roll_state = diag_positions.get_roll_state(instrument_code)
        if roll_state not in ["Force", "Force_Outright"]:
            return False
        else:
            return True


def create_force_roll_orders(data, instrument_code):
    """

    :param data:
    :param instrument_code:
    :return: tuple; instrument_order (or missing_order), contract_orders
    """
    diag_positions = diagPositions(data)
    roll_state = diag_positions.get_roll_state(instrument_code)

    strategy = ROLL_PSEUDO_STRATEGY
    trade = 0
    instrument_order = instrumentOrder(
        strategy,
        instrument_code,
        trade,
        roll_order=True,
        order_type="Zero-roll-order")

    diag_contracts = diagContracts(data)
    priced_contract_id = diag_contracts.get_priced_contract_id(instrument_code)
    forward_contract_id = diag_contracts.get_forward_contract_id(
        instrument_code)
    position_in_priced = diag_positions.get_position_for_instrument_and_contract_date(
        instrument_code, priced_contract_id)

    if position_in_priced == 0:
        return missing_order, []

    if roll_state == "Force_Outright":
        contract_orders = create_contract_orders_outright(
            data,
            instrument_code,
            priced_contract_id,
            forward_contract_id,
            position_in_priced,
        )
    elif roll_state == "Force":
        contract_orders = create_contract_orders_spread(
            data,
            instrument_code,
            priced_contract_id,
            forward_contract_id,
            position_in_priced,
        )
    else:
        raise Exception("Roll state %s not recognised" % roll_state)

    contract_orders = allocate_algo_to_list_of_contract_orders(
        data, contract_orders, instrument_order=instrument_order
    )

    return instrument_order, contract_orders


def create_contract_orders_outright(
        data,
        instrument_code,
        priced_contract_id,
        forward_contract_id,
        position_in_priced):
    diag_prices = diagPrices(data)
    reference_price_priced_contract, reference_price_forward_contract = tuple(
        diag_prices.get_last_matched_prices_for_contract_list(
            instrument_code, [priced_contract_id, forward_contract_id]
        )
    )
    strategy = ROLL_PSEUDO_STRATEGY

    first_order = contractOrder(
        strategy,
        instrument_code,
        priced_contract_id,
        -position_in_priced,
        reference_price=reference_price_priced_contract,
        roll_order=True,
        inter_spread_order=True,
    )
    second_order = contractOrder(
        strategy,
        instrument_code,
        forward_contract_id,
        position_in_priced,
        reference_price=reference_price_forward_contract,
        roll_order=True,
        inter_spread_order=True,
    )

    return [first_order, second_order]


def create_contract_orders_spread(
        data,
        instrument_code,
        priced_contract_id,
        forward_contract_id,
        position_in_priced):

    diag_prices = diagPrices(data)
    reference_price_priced_contract, reference_price_forward_contract = tuple(
        diag_prices.get_last_matched_prices_for_contract_list(
            instrument_code, [priced_contract_id, forward_contract_id]
        )
    )

    strategy = ROLL_PSEUDO_STRATEGY
    contract_id_list = [priced_contract_id, forward_contract_id]
    trade_list = [-position_in_priced, position_in_priced]
    spread_reference_price = (
        reference_price_priced_contract - reference_price_forward_contract
    )

    spread_order = contractOrder(
        strategy,
        instrument_code,
        contract_id_list,
        trade_list,
        reference_price=spread_reference_price,
        roll_order=True,
    )

    return [spread_order]
