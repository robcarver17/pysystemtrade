import numpy as np

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

from syscore.genutils import sign
from syscore.objects import (
    missing_order,
    missing_contract,
    missing_data,
    rolling_cant_trade,
)

from sysproduction.data.contracts import diagContracts
from sysproduction.data.positions import diagPositions
from sysproduction.data.prices import diagPrices
from sysproduction.data.controls import dataLocks

from sysexecution.contract_orders import contractOrder
from sysexecution.algos.allocate_algo_to_order import (
    allocate_algo_to_list_of_contract_orders,
)
from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore


class stackHandlerForSpawning(stackHandlerCore):
    def spawn_children_from_new_instrument_orders(self):
        new_order_ids = self.instrument_stack.list_of_new_orders()
        for instrument_order_id in new_order_ids:
            self.spawn_children_from_instrument_order_id(instrument_order_id)

    def spawn_children_from_instrument_order_id(self, instrument_order_id):
        data_locks = dataLocks(self.data)
        instrument_order = self.instrument_stack.get_order_with_id_from_stack(
            instrument_order_id
        )
        if instrument_order is missing_order:
            return failure

        log = instrument_order.log_with_attributes(self.log)
        instrument_locked = data_locks.is_instrument_locked(
            instrument_order.instrument_code
        )
        if instrument_locked:
            log.msg("Instrument is locked, not spawning order")
            return failure

        list_of_contract_orders = spawn_children_from_instrument_order(
            self.data, instrument_order
        )

        log.msg(
            "List of contract orders spawned %s" %
            str(list_of_contract_orders))

        result = self.add_children_to_stack_and_child_id_to_parent(
            self.instrument_stack,
            self.contract_stack,
            instrument_order,
            list_of_contract_orders,
        )

        return result


def spawn_children_from_instrument_order(data, instrument_order):
    spawn_function = function_to_process_instrument(
        instrument_order.instrument_code)
    list_of_contract_orders = spawn_function(data, instrument_order)
    list_of_contract_orders = allocate_algo_to_list_of_contract_orders(
        data, list_of_contract_orders, instrument_order=instrument_order
    )

    return list_of_contract_orders


def function_to_process_instrument(instrument_code):
    """
    FIX ME in future this will handle spread orders, but for now is only for 'single instruments'

    :param instrument_code:
    :return: function
    """
    function_dict = dict(
        single_instrument=single_instrument_child_orders,
        inter_market=inter_market_instrument_child_orders,
        intra_market=intra_market_instrument_child_orders,
    )
    instrument_type = "single_instrument"

    required_function = function_dict[instrument_type]

    return required_function


def single_instrument_child_orders(data, instrument_order):
    """
    Generate child orders for a single instrument (not rolls)

    :param data: dataBlob. Required as uses roll data to determine appropriate instrument
    :param instrument_order:
    :return: A list of contractOrders to submit to the stack
    """
    # We don't allow zero trades to be spawned
    # Zero trades can enter the instrument stack, where they can potentially
    # modify existing trades
    if instrument_order.is_zero_trade():
        return []

    # Get required contract(s) depending on roll status
    list_of_child_contract_dates_and_trades = (
        get_required_contract_trade_for_instrument(data, instrument_order)
    )
    if list_of_child_contract_dates_and_trades is rolling_cant_trade:
        return []

    list_of_contract_orders = list_of_contract_orders_from_list_of_child_date_and_trade(
        instrument_order, list_of_child_contract_dates_and_trades)

    # Get reference price for relevant contract(s)
    # used for TCA
    # Adjust price if reference contract is different from required contract
    list_of_contract_orders = calculate_reference_prices_for_direct_child_orders(
        data, instrument_order, list_of_contract_orders)

    # Now get the limit prices, where relevant
    # Adjust limit price if limit_contract is different from required contract
    list_of_contract_orders = calculate_limit_prices_for_direct_child_orders(
        data, instrument_order, list_of_contract_orders
    )

    return list_of_contract_orders


def get_required_contract_trade_for_instrument(data, instrument_order):
    """
    Return the contract to trade for a given instrument

    Depends on roll status and trade vs position:
     - roll_states = ['No_Roll', 'Passive', 'Force', 'Force_Outright', 'Roll_Adjusted']

    If 'No Roll' then trade current contract
    If 'Passive', and no position in current contract: trade next contract
    If 'Passive', and reducing trade which leaves zero or something in current contract: trade current contract
    If 'Passive', and reducing trade which is larger than current contract position: trade current and next contract
    If 'Passive', and increasing trade: trade next contract
    If 'Force' or 'Force Outright' or 'Roll_Adjusted': don't trade

    :param instrument_order:
    :param data: dataBlog
    :return: tuple: list of child orders: each is a tuple: contract str or missing_contract, trade int
    """
    instrument_code = instrument_order.instrument_code
    log = instrument_order.log_with_attributes(data.log)
    trade = instrument_order.trade.as_int()
    if trade is missing_order:
        log.critical("Instrument order can't be a spread order")
        return missing_contract

    diag_contracts = diagContracts(data)
    current_contract = diag_contracts.get_priced_contract_id(instrument_code)
    next_contract = diag_contracts.get_forward_contract_id(instrument_code)

    diag_positions = diagPositions(data)
    roll_state = diag_positions.get_roll_state(instrument_code)

    position_current_contract = (
        diag_positions.get_position_for_instrument_and_contract_date(
            instrument_code, current_contract
        )
    )
    if roll_state == "No_Roll":
        log.msg(
            "No roll, allocating entire order %s to current contract %s"
            % (str(instrument_order), current_contract)
        )
        return [(current_contract, trade)]

    elif roll_state in ["Force", "Force_Outright", "Roll_Adjusted"]:
        log.msg(
            "Roll state %s is rolling, not going to generate trade for order %s" %
            (roll_state, str(instrument_order)))
        return rolling_cant_trade

    elif roll_state == "Passive":
        return passive_roll_child_order(
            position_current_contract,
            current_contract,
            next_contract,
            trade,
            log,
            instrument_order,
        )
    else:
        log.critical(
            "Roll state %s not understood: can't generate trade for %s"
            % (roll_state, str(instrument_order))
        )
        return missing_contract


def passive_roll_child_order(
    position_current_contract,
    current_contract,
    next_contract,
    trade,
    log,
    instrument_order,
):
    # Break out because so darn complicated
    if position_current_contract == 0:
        # Passive roll and no position in the current contract, start trading
        # the next
        log.msg(
            "Passive roll handling order %s, no position in current contract, entire trade in next contract %s" %
            (str(instrument_order), next_contract))
        return [(next_contract, trade)]

    # ok still have a position in the current contract
    increasing_trade = sign(trade) == sign(position_current_contract)
    if increasing_trade:
        # Passive roll and increasing trade
        # Do it all in next contract
        log.msg(
            "Passive roll handling order %s, increasing trade, entire trade in next contract %s" %
            (str(instrument_order), next_contract))
        return [(next_contract, trade)]

    # ok a reducing trade
    new_position = position_current_contract + trade
    sign_of_position_is_unchanged = sign(position_current_contract) == sign(
        new_position
    )
    if new_position == 0 or sign_of_position_is_unchanged:
        # A reducing trade that we can do entirely in the current contract
        log.msg(
            "Passive roll handling order %s, reducing trade, entire trade in next contract %s" %
            (str(instrument_order), next_contract))
        return [(current_contract, trade)]

    # OKAY to recap: it's a passive roll, but the trade will be split between
    # current and next
    log.msg(
        "Passive roll handling order %s, reducing trade, split trade between contract %s and %s" %
        (str(instrument_order), current_contract, next_contract))

    trade_in_current_contract = -position_current_contract
    trade_in_next_contract = trade - trade_in_current_contract

    return [
        (current_contract, trade_in_current_contract),
        (next_contract, trade_in_next_contract),
    ]


def list_of_contract_orders_from_list_of_child_date_and_trade(
    instrument_order, list_of_child_contract_dates_and_trades
):

    list_of_contract_orders = [
        contract_order_for_direct_instrument_child_date_and_trade(
            instrument_order, child_date_and_trade
        )
        for child_date_and_trade in list_of_child_contract_dates_and_trades
    ]

    return list_of_contract_orders


def contract_order_for_direct_instrument_child_date_and_trade(
    instrument_order, child_date_and_trade
):
    """
    Gets a child contract order from a parent instrument order where the instrument is 'direct'
       eg the instrument name is the same as the instrument traded
       (This will not be the case for inter market orders)

    :param instrument_order: original parent order
    :param child_date_and_trade:
    :return: contractOrder. Fields reference_price, algo_to_use, limit_price will be set later
    """
    if child_date_and_trade is None:
        return None
    child_contract, child_trade = child_date_and_trade
    parent_id = instrument_order.order_id
    strategy = instrument_order.strategy_name
    instrument = instrument_order.instrument_code

    child_contract_order = contractOrder(
        strategy,
        instrument,
        child_contract,
        child_trade,
        parent=parent_id,
    )

    return child_contract_order


def intra_market_instrument_child_orders(data, instrument_order):
    """
    Generate child orders for intra-market instrument (not rolls)

    :param data: dataBlob. Required as uses roll data to determine appropriate instrument
    :param instrument_order:
    :return: A list of contractOrders to submit to the stack
    """

    # Get required contracts depending on roll status

    # Get reference price for relevant contract spread

    # Adjust limit price if limit_contracts is different from required
    # contracts

    raise NotImplementedError


def inter_market_instrument_child_orders(data, instrument_order):
    """
    Generate child orders for inter market instrument (not rolls)

    :param data: dataBlob. Required as uses roll data to determine appropriate instrument
    :param instrument_order:
    :return: A list of contractOrders to submit to the stack
    """

    # Get required contracts depending on roll status

    # Get reference price for relevant contract spread

    # Adjust limit price if limit_contracts is different from required
    # contracts

    raise NotImplementedError


def calculate_reference_prices_for_direct_child_orders(
    data, instrument_order, list_of_contract_orders
):
    """
    A direct child order only contains one contract id i.e. not an intramarket spread

    :param data:
    :param instrument_order:
    :param list_of_contract_orders:
    :return:
    """
    list_of_contract_orders = [
        add_reference_price_to_a_direct_child_order(data, instrument_order, child_order)
        for child_order in list_of_contract_orders
    ]

    return list_of_contract_orders


def add_reference_price_to_a_direct_child_order(
        data, instrument_order, child_order):
    """

    :param data: dataBlob
    :param instrument_order:
    :param child_order: will be modified
    :return: child order
    """

    instrument_code = instrument_order.instrument_code
    contract_to_match = instrument_order.reference_contract
    price_to_adjust = instrument_order.reference_price

    if contract_to_match is None or price_to_adjust is None:
        # No reference price so don't bother
        return child_order

    new_reference_price = calculate_adjusted_price_for_a_direct_child_order(
        data, instrument_code, child_order, contract_to_match, price_to_adjust
    )

    if new_reference_price is missing_data:
        data.log.warn(
            "Couldn't adjust reference price for order %s child %s going from %s to %s, can't do TCA" %
            (str(instrument_order),
             str(child_order),
                contract_to_match,
                child_order.contract_id,
             ),
            instrument_order_id=instrument_order.order_id,
            strategy_name=instrument_order.strategy_name,
            instrument_code=instrument_code.instrument_code,
        )
        return child_order

    child_order.reference_price = new_reference_price

    return child_order


def calculate_adjusted_price_for_a_direct_child_order(
    data, instrument_code, child_order, original_contract_date, original_price
):
    """

    :param data:
    :param instrument_code:
    :param child_order:
    :param original_contract_date:
    :param original_price:
    :return: float or missing data
    """

    try:
        assert len(child_order.contract_id) == 1
    except BaseException:
        raise Exception(
            "You have tried to adjust the price for a spread contract order assuming it is a direct order"
        )

    child_contract_date = child_order.contract_id[0]

    if original_contract_date == child_contract_date:
        return original_price

    diag_prices = diagPrices(data)
    contract_list = [original_contract_date, child_contract_date]
    list_of_prices = diag_prices.get_last_matched_prices_for_contract_list(
        instrument_code, contract_list
    )
    differential = list_of_prices[1] - list_of_prices[0]

    if np.isnan(differential):
        # can't adjust
        # note need to test code there may be other ways in which this fails
        return missing_data

    adjusted_price = original_price + differential

    return adjusted_price


def calculate_limit_prices_for_direct_child_orders(
    data, instrument_order, list_of_contract_orders
):
    """
    A direct child order only contains one contract id i.e. not an intramarket spread

    :param data:
    :param instrument_order:
    :param list_of_contract_orders:
    :return: list of contract orders
    """
    list_of_contract_orders = [
        add_limit_price_to_a_direct_child_order(data, instrument_order, child_order)
        for child_order in list_of_contract_orders
    ]

    flag_missing_orders = [
        child_order is missing_order for child_order in list_of_contract_orders
    ]
    if any(flag_missing_orders):
        data.log.critical(
            "Couldn't adjust limit price for at least one child order %s: can't execute any child orders" %
            str(instrument_order),
            instrument_order_id=instrument_order.order_id,
            strategy_name=instrument_order.strategy_name,
            instrument_code=instrument_order.instrument_code,
        )
        return []

    return list_of_contract_orders


def add_limit_price_to_a_direct_child_order(
        data, instrument_order, child_order):
    """

    :param data: dataBlob
    :param instrument_order:
    :param child_order: will be modified
    :return: float
    """

    instrument_code = instrument_order.instrument_code
    contract_to_match = instrument_order.limit_contract
    price_to_adjust = instrument_order.limit_price

    if contract_to_match is None or price_to_adjust is None:
        # No limit price so don't bother
        return child_order

    new_limit_price = calculate_adjusted_price_for_a_direct_child_order(
        data, instrument_code, child_order, contract_to_match, price_to_adjust
    )
    if new_limit_price is missing_data:
        # This is a serious problem
        # We can't possibly execute any part of the parent order
        data.log.critical(
            "Couldn't adjust limit price for order %s child %s going from %s to %s" %
            (str(instrument_order),
             str(child_order),
                contract_to_match,
                child_order.contract_id,
             ),
            instrument_order_id=instrument_order.order_id,
            strategy_name=instrument_order.strategy_name,
            instrument_code=instrument_order.instrument_code,
        )
        return missing_order

    child_order.limit_price = new_limit_price

    return child_order
