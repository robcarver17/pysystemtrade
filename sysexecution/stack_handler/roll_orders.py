import datetime
from dataclasses import dataclass
from sysexecution.orders.named_order_objects import missing_order
from sysobjects.production.roll_state import roll_close_state
from syscore.constants import named_object
from syscore.genutils import same_sign
from sysdata.data_blob import dataBlob

from sysexecution.orders.instrument_orders import instrumentOrder
from sysexecution.algos.allocate_algo_to_order import (
    allocate_algo_to_list_of_contract_orders,
)
from sysexecution.order_stacks.instrument_order_stack import instrumentOrderStackData

from sysobjects.contracts import futuresContract

from sysproduction.data.positions import diagPositions
from sysproduction.data.contracts import dataContracts
from sysproduction.data.prices import diagPrices
from sysproduction.data.positions import updatePositions

from sysexecution.stack_handler.stackHandlerCore import stackHandlerCore
from sysexecution.orders.contract_orders import contractOrder, best_order_type
from sysexecution.orders.instrument_orders import zero_roll_order_type

from sysexecution.orders.list_of_orders import listOfOrders

CONTRACT_ORDER_TYPE_FOR_ROLL_ORDERS = best_order_type

ROLL_PSEUDO_STRATEGY = "_ROLL_PSEUDO_STRATEGY"


class stackHandlerForRolls(stackHandlerCore):
    def generate_force_roll_orders(self):
        diag_positions = diagPositions(self.data)
        list_of_instruments = (
            diag_positions.get_list_of_instruments_with_current_positions()
        )
        for instrument_code in list_of_instruments:
            self.generate_force_roll_orders_for_instrument(instrument_code)

    def generate_force_roll_orders_for_instrument(self, instrument_code: str):
        auto_update_roll_status(self.data, instrument_code)
        no_roll_required = not self.check_roll_required_and_safe(instrument_code)
        if no_roll_required:
            return None

        self.generate_force_roll_orders_for_instrument_without_checking(instrument_code)

    def generate_force_roll_orders_for_instrument_without_checking(
        self, instrument_code: str
    ):
        instrument_order, list_of_contract_orders = create_force_roll_orders(
            self.data, instrument_code
        )
        # Create a pseudo instrument order and a set of contract orders
        # This will also prevent trying to generate more than one set of roll
        # orders

        if (
            list_of_contract_orders is missing_order
            or instrument_order is missing_order
        ):
            # No orders
            return

        self.add_instrument_and_list_of_contract_orders_to_stack(
            instrument_order,
            list_of_contract_orders,
        )

    def check_roll_required_and_safe(self, instrument_code: str) -> bool:
        roll_orders_required_from_positions = (
            self.check_if_positions_require_order_generation(instrument_code)
        )
        if not roll_orders_required_from_positions:
            ## if we don't exit here will get errors even it we're not rolling
            return False

        roll_orders_required_from_roll_state = (
            self.check_if_roll_state_requires_order_generation(instrument_code)
        )
        if not roll_orders_required_from_roll_state:
            ## if we don't exit here will get errors even it we're not rolling
            return False

        safe_to_roll = self.check_if_safe_to_add_roll_order(instrument_code)

        if not safe_to_roll:
            return False

        return safe_to_roll

    def check_if_positions_require_order_generation(self, instrument_code: str) -> bool:
        position_in_priced = get_position_in_priced(
            data=self.data, instrument_code=instrument_code
        )
        return position_in_priced != 0

    def check_if_roll_state_requires_order_generation(
        self, instrument_code: str
    ) -> bool:
        diag_positions = diagPositions(self.data)
        roll_state_requires_order_generation = (
            diag_positions.is_roll_state_requiring_order_generation(instrument_code)
        )
        if not roll_state_requires_order_generation:
            return False

        order_generation_is_appropriate = (
            self.check_if_order_required_given_roll_state_is_appropriate(
                instrument_code
            )
        )

        return order_generation_is_appropriate

    def check_if_order_required_given_roll_state_is_appropriate(
        self, instrument_code: str
    ):
        diag_positions = diagPositions(self.data)

        ## double sided state implies we roll force or force_leg
        double_sided = diag_positions.is_double_sided_trade_roll_state(instrument_code)
        if not double_sided:
            ## definitely doing this no further checks required
            return True

        order_generation_is_appropriate = (
            self.check_if_order_required_in_double_sided_roll_state(instrument_code)
        )

        return order_generation_is_appropriate

    def check_if_order_required_in_double_sided_roll_state(self, instrument_code: str):
        ## Double sided, so we will only do if there is no reducing order on the stack
        has_reducing_order = has_reducing_instrument_order_on_stack(
            data=self.data,
            instrument_stack=self.instrument_stack,
            instrument_code=instrument_code,
        )
        has_no_reducing_order = not has_reducing_order

        ## only okay to do double sided if no reducing order
        return has_no_reducing_order

    def check_if_safe_to_add_roll_order(self, instrument_code: str) -> bool:
        roll_order_already_on_stack = self.check_if_roll_order_already_on_stack(
            instrument_code
        )
        if roll_order_already_on_stack:
            ## already put roll order on stack
            return False

        ## Check other strategies for orders
        ##  (note this will return True if it's a roll order so we'd get an email if we hadn't already exited)
        any_order_for_instrument_already_on_stack = (
            self.check_and_warn_if_order_for_instrument_already_on_contract_stack(
                instrument_code
            )
        )
        true_if_no_orders_already_on_stack = (
            not any_order_for_instrument_already_on_stack
        )

        return true_if_no_orders_already_on_stack

    def check_if_roll_order_already_on_stack(self, instrument_code: str) -> bool:
        order_already_on_stack = self.instrument_stack.does_strategy_and_instrument_already_have_order_on_stack(
            ROLL_PSEUDO_STRATEGY, instrument_code
        )

        return order_already_on_stack

    def check_and_warn_if_order_for_instrument_already_on_contract_stack(
        self, instrument_code: str
    ) -> bool:
        orders_already_on_stack = (
            self.contract_stack.does_stack_have_orders_for_instrument_code(
                instrument_code
            )
        )

        if orders_already_on_stack:
            ## Need to warn user so they can take action if required

            self.log.critical(
                "Cannot force roll %s as already other orders on contract stack"
                % (instrument_code),
                instrument_code=instrument_code,
            )

        return orders_already_on_stack

    def add_instrument_and_list_of_contract_orders_to_stack(
        self, instrument_order: instrumentOrder, list_of_contract_orders: listOfOrders
    ):
        instrument_stack = self.instrument_stack
        contract_stack = self.contract_stack
        log_attrs = {**instrument_order.log_attributes(), "method": "temp"}

        # Do as a transaction: if everything doesn't go to plan can roll back
        # We lock now, and
        instrument_order.lock_order()
        try:
            parent_order_id = instrument_stack.put_order_on_stack(
                instrument_order, allow_zero_orders=True
            )

        except Exception as parent_order_error:
            self.log.warning(
                "Couldn't put parent order %s on instrument order stack error %s"
                % (str(instrument_order), str(parent_order_error)),
                **log_attrs,
            )
            instrument_order.unlock_order()
            return None

        ## Parent order is now on stack in locked state
        ## We will unlock at the end, or during a rollback

        # Do as a transaction: if everything doesn't go to plan can roll back
        # if this try fails we will roll back the instrument commit
        list_of_child_order_ids = []

        try:
            # Add parent order to children
            # This will only throw an error if the orders already have parents, which they shouldn't
            for child_order in list_of_contract_orders:
                child_order.parent = parent_order_id

            # this will return either -
            #     - a list of order IDS if all went well
            #     - an empty list if error and rolled back,
            #      - or an error something went wrong and couldn't rollback (the outer catch will try and rollback)
            list_of_child_order_ids = self.put_children_on_stack(
                child_stack=contract_stack,
                list_of_child_orders=list_of_contract_orders,
                parent_order=instrument_order,
            )

            if len(list_of_child_order_ids) == 0:
                ## We had an error, but manged to roll back the children. Still need to throw an error so the parent
                ##   will be rolledback. But because the list_of_child_order_ids is probably zero
                ##   we won't try and rollback children in the catch statement
                raise Exception(
                    "Couldn't put child orders on stack, children were rolled back okay"
                )

            ## All seems to have worked

            # still locked remember
            instrument_stack.unlock_order_on_stack(parent_order_id)
            instrument_stack.add_children_to_order_without_existing_children(
                parent_order_id, list_of_child_order_ids
            )

        except Exception as error_from_adding_child_orders:
            # okay it's gone wrong
            # Roll back parent order and possibly children
            # At this point list_of_child_order_ids will either be empty (if succesful rollback) or contain child ids

            self.rollback_parents_and_children_and_handle_exceptions(
                child_stack=contract_stack,
                parent_stack=instrument_stack,
                list_of_child_order_ids=list_of_child_order_ids,
                parent_order=instrument_order,
                error_from_adding_child_orders=error_from_adding_child_orders,
            )

        # phew got there
        self.log.debug(
            "Added parent order with ID %d %s to stack"
            % (parent_order_id, str(instrument_order)),
            **log_attrs,
        )
        self.log_successful_adding(
            list_of_child_orders=list_of_contract_orders,
            list_of_child_ids=list_of_child_order_ids,
            parent_order=instrument_order,
        )


def create_force_roll_orders(
    data: dataBlob, instrument_code: str
) -> (instrumentOrder, listOfOrders):
    """

    :param data:
    :param instrument_code:
    :return: tuple; instrument_order (or missing_order), contract_orders
    """
    roll_spread_info = get_roll_spread_information(data, instrument_code)
    type_of_roll = flat_roll_or_close_near_contract(data, instrument_code)
    instrument_order = create_instrument_roll_order(
        data=data,
        roll_spread_info=roll_spread_info,
        instrument_code=instrument_code,
        type_of_roll=type_of_roll,
    )

    list_of_contract_orders = create_contract_roll_orders(
        data=data,
        roll_spread_info=roll_spread_info,
        instrument_order=instrument_order,
        type_of_roll=type_of_roll,
    )

    return instrument_order, list_of_contract_orders


roll_state_is_flat_roll = named_object("flat_roll")
roll_state_is_close_near_contract = named_object("close_near_contract")


def flat_roll_or_close_near_contract(data: dataBlob, instrument_code: str):
    diag_positions = diagPositions(data)
    roll_state = diag_positions.get_roll_state(instrument_code)

    if roll_state is roll_close_state:
        ## close near contract
        return roll_state_is_close_near_contract
    else:
        ## force or force outright
        return roll_state_is_flat_roll


@dataclass
class rollSpreadInformation:
    instrument_code: str
    priced_contract_id: str
    forward_contract_id: str
    position_in_priced: int
    reference_price_priced_contract: float
    reference_price_forward_contract: float
    reference_date: datetime.datetime

    @property
    def reference_price_spread(self) -> float:
        return (
            self.reference_price_priced_contract - self.reference_price_forward_contract
        )


def get_roll_spread_information(
    data: dataBlob, instrument_code: str
) -> rollSpreadInformation:
    diag_contracts = dataContracts(data)
    diag_prices = diagPrices(data)

    priced_contract_id = diag_contracts.get_priced_contract_id(instrument_code)
    forward_contract_id = diag_contracts.get_forward_contract_id(instrument_code)

    position_in_priced = get_position_in_priced(
        data=data, instrument_code=instrument_code
    )

    reference_date, last_matched_prices = tuple(
        diag_prices.get_last_matched_date_and_prices_for_contract_list(
            instrument_code, [priced_contract_id, forward_contract_id]
        )
    )
    (
        reference_price_priced_contract,
        reference_price_forward_contract,
    ) = last_matched_prices

    return rollSpreadInformation(
        priced_contract_id=priced_contract_id,
        forward_contract_id=forward_contract_id,
        reference_price_forward_contract=reference_price_forward_contract,
        reference_price_priced_contract=reference_price_priced_contract,
        position_in_priced=int(position_in_priced),
        reference_date=reference_date,
        instrument_code=instrument_code,
    )


def get_position_in_priced(data: dataBlob, instrument_code: str) -> int:
    diag_positions = diagPositions(data)
    diag_contracts = dataContracts(data)

    priced_contract_id = diag_contracts.get_priced_contract_id(instrument_code)

    contract = futuresContract(instrument_code, priced_contract_id)

    position_in_priced = int(diag_positions.get_position_for_contract(contract))

    return position_in_priced


def create_instrument_roll_order(
    data: dataBlob,
    roll_spread_info: rollSpreadInformation,
    instrument_code: str,
    type_of_roll: named_object,
) -> instrumentOrder:
    if type_of_roll is roll_state_is_flat_roll:
        instrument_order = create_instrument_roll_order_for_flat_roll(
            roll_spread_info=roll_spread_info, instrument_code=instrument_code
        )
    else:
        instrument_order = create_instrument_roll_order_closing_priced_contract(
            data=data,
            roll_spread_info=roll_spread_info,
            instrument_code=instrument_code,
        )

    return instrument_order


def create_instrument_roll_order_for_flat_roll(
    roll_spread_info: rollSpreadInformation,
    instrument_code: str,
) -> instrumentOrder:
    strategy = ROLL_PSEUDO_STRATEGY
    trade = 0
    instrument_order = instrumentOrder(
        strategy,
        instrument_code,
        trade,
        roll_order=True,
        order_type=zero_roll_order_type,
        reference_price=roll_spread_info.reference_price_spread,
        reference_contract=ROLL_PSEUDO_STRATEGY,
        reference_datetime=roll_spread_info.reference_date,
    )

    return instrument_order


def create_instrument_roll_order_closing_priced_contract(
    data: dataBlob,
    roll_spread_info: rollSpreadInformation,
    instrument_code: str,
) -> instrumentOrder:
    strategy = get_strategy_name_with_largest_position_for_instrument(
        data=data, instrument_code=instrument_code
    )
    position_priced = roll_spread_info.position_in_priced

    trade = -position_priced
    instrument_order = instrumentOrder(
        strategy,
        instrument_code,
        trade,
        roll_order=True,
        order_type=best_order_type,
        reference_price=roll_spread_info.reference_price_spread,
        reference_contract=ROLL_PSEUDO_STRATEGY,
        reference_datetime=roll_spread_info.reference_date,
    )

    return instrument_order



def get_strategy_name_with_largest_position_for_instrument(
    data: dataBlob, instrument_code: str
) -> str:
    diag_positions = diagPositions(data)
    all_instrument_positions = (
        diag_positions.get_all_current_strategy_instrument_positions()
    )

    try:
        strategy_name = all_instrument_positions.strategy_name_with_largest_abs_position_for_instrument(
            instrument_code
        )
    except:
        ## corner case where nets out to 0
        strategies = diag_positions.get_list_of_strategies_with_positions()
        strategy_name = strategies[0]
        data.log.debug(
            "No strategies have net positions in %s, using arbitrary strategy %s"
            % (instrument_code, strategy_name)
        )

    return strategy_name


def create_contract_roll_orders(
    data: dataBlob,
    roll_spread_info: rollSpreadInformation,
    instrument_order: instrumentOrder,
    type_of_roll: named_object,
) -> listOfOrders:
    diag_positions = diagPositions(data)
    instrument_code = instrument_order.instrument_code

    if roll_spread_info.position_in_priced == 0:
        return missing_order

    if type_of_roll is roll_state_is_close_near_contract:
        contract_orders = create_contract_orders_close_first_contract(
            roll_spread_info=roll_spread_info, instrument_order=instrument_order
        )

    elif diag_positions.is_roll_state_force(instrument_code):
        contract_orders = create_contract_orders_spread(roll_spread_info)

    elif diag_positions.is_roll_state_force_outright(instrument_code):
        contract_orders = create_contract_orders_outright(roll_spread_info)

    else:
        roll_state = diag_positions.get_roll_state(instrument_code)
        data.log.warning(
            "Roll state %s is unexpected, might have changed" % str(roll_state),
            **instrument_order.log_attributes(),
            method="temp",
        )
        return missing_order

    contract_orders = allocate_algo_to_list_of_contract_orders(
        data, contract_orders, instrument_order
    )

    return contract_orders


def create_contract_orders_close_first_contract(
    roll_spread_info: rollSpreadInformation, instrument_order: instrumentOrder
) -> listOfOrders:
    strategy = instrument_order.strategy_name

    first_order = contractOrder(
        strategy,
        instrument_order.instrument_code,
        roll_spread_info.priced_contract_id,
        -roll_spread_info.position_in_priced,
        reference_price=roll_spread_info.reference_price_priced_contract,
        roll_order=True,
        order_type=CONTRACT_ORDER_TYPE_FOR_ROLL_ORDERS,
    )

    return listOfOrders([first_order])


def create_contract_orders_outright(
    roll_spread_info: rollSpreadInformation,
) -> listOfOrders:
    strategy = ROLL_PSEUDO_STRATEGY

    first_order = contractOrder(
        strategy,
        roll_spread_info.instrument_code,
        roll_spread_info.priced_contract_id,
        -roll_spread_info.position_in_priced,
        reference_price=roll_spread_info.reference_price_priced_contract,
        roll_order=True,
        order_type=CONTRACT_ORDER_TYPE_FOR_ROLL_ORDERS,
    )
    second_order = contractOrder(
        strategy,
        roll_spread_info.instrument_code,
        roll_spread_info.forward_contract_id,
        roll_spread_info.position_in_priced,
        reference_price=roll_spread_info.reference_price_forward_contract,
        roll_order=True,
        order_type=CONTRACT_ORDER_TYPE_FOR_ROLL_ORDERS,
    )

    return listOfOrders([first_order, second_order])


def create_contract_orders_spread(
    roll_spread_info: rollSpreadInformation,
) -> listOfOrders:
    strategy = ROLL_PSEUDO_STRATEGY
    contract_id_list = [
        roll_spread_info.priced_contract_id,
        roll_spread_info.forward_contract_id,
    ]
    trade_list = [
        -roll_spread_info.position_in_priced,
        roll_spread_info.position_in_priced,
    ]

    spread_order = contractOrder(
        strategy,
        roll_spread_info.instrument_code,
        contract_id_list,
        trade_list,
        reference_price=roll_spread_info.reference_price_spread,
        roll_order=True,
        order_type=CONTRACT_ORDER_TYPE_FOR_ROLL_ORDERS,
    )

    return listOfOrders([spread_order])


def auto_update_roll_status(data: dataBlob, instrument_code: str):
    update_positions = updatePositions(data)
    update_positions.check_and_auto_update_roll_state(instrument_code)


def has_reducing_instrument_order_on_stack(
    data: dataBlob, instrument_stack: instrumentOrderStackData, instrument_code: str
) -> bool:
    list_of_orders = instrument_stack.list_of_orders_with_instrument_code(
        instrument_code
    )
    if len(list_of_orders) > 1:
        ## can't evaluate
        return False
    elif len(list_of_orders) == 0:
        ## definitely not
        return False

    ## okay we have one order, but is it reducing?
    order = list_of_orders[0]
    return is_order_reducing_order(data=data, order=order)


def is_order_reducing_order(data: dataBlob, order: instrumentOrder) -> bool:
    diag_positions = diagPositions(data)
    position_in_priced_contract = (
        diag_positions.get_position_in_priced_contract_for_instrument(
            order.instrument_code
        )
    )
    trade = order.trade.as_single_trade_qty_or_error()

    return is_trade_reducing_position(trade=trade, position=position_in_priced_contract)


def is_trade_reducing_position(trade: int, position: float) -> bool:
    if same_sign(trade, position):
        return False
    ## Note it could be the case that abs(trade)>abs(position), but we still return True here

    return True
