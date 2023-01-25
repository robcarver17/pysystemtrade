import datetime
from dataclasses import dataclass
from sysexecution.orders.named_order_objects import missing_order

from sysdata.data_blob import dataBlob

from sysexecution.orders.instrument_orders import instrumentOrder
from sysexecution.algos.allocate_algo_to_order import (
    allocate_algo_to_list_of_contract_orders,
)

from sysobjects.contracts import futuresContract

from sysproduction.data.positions import diagPositions
from sysproduction.data.contracts import dataContracts
from sysproduction.data.prices import diagPrices

from sysexecution.stack_handler.stackHandlerCore import (
    stackHandlerCore,
    put_children_on_stack,
    rollback_parents_and_children_and_handle_exceptions,
    log_successful_adding,
)
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
        no_roll_required = not self.check_roll_required(instrument_code)
        if no_roll_required:
            return None

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
            return None

        self.add_instrument_and_list_of_contract_orders_to_stack(
            instrument_order,
            list_of_contract_orders,
        )

    def check_roll_required(self, instrument_code: str) -> bool:

        order_already_on_stack = self.check_if_roll_order_already_on_stack(
            instrument_code
        )
        forced_roll_required = self.check_if_forced_roll_required(instrument_code)

        if order_already_on_stack:
            return False

        if forced_roll_required:
            return True
        else:
            return False

    def check_if_roll_order_already_on_stack(self, instrument_code: str) -> bool:
        order_already_on_stack = self.instrument_stack.does_strategy_and_instrument_already_have_order_on_stack(
            ROLL_PSEUDO_STRATEGY, instrument_code
        )

        return order_already_on_stack

    def check_if_forced_roll_required(self, instrument_code: str) -> bool:
        diag_positions = diagPositions(self.data)
        forced_roll_required = diag_positions.is_forced_roll_required(instrument_code)

        return forced_roll_required

    def add_instrument_and_list_of_contract_orders_to_stack(
        self, instrument_order: instrumentOrder, list_of_contract_orders: listOfOrders
    ):

        instrument_stack = self.instrument_stack
        contract_stack = self.contract_stack
        parent_log = instrument_order.log_with_attributes(self.log)

        # Do as a transaction: if everything doesn't go to plan can roll back
        # We lock now, and
        instrument_order.lock_order()
        try:
            parent_order_id = instrument_stack.put_order_on_stack(
                instrument_order, allow_zero_orders=True
            )

        except Exception as parent_order_error:
            parent_log.warn(
                "Couldn't put parent order %s on instrument order stack error %s"
                % (str(instrument_order), str(parent_order_error))
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
            list_of_child_order_ids = put_children_on_stack(
                child_stack=contract_stack,
                parent_log=parent_log,
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

            rollback_parents_and_children_and_handle_exceptions(
                child_stack=contract_stack,
                parent_stack=instrument_stack,
                list_of_child_order_ids=list_of_child_order_ids,
                parent_order_id=parent_order_id,
                error_from_adding_child_orders=error_from_adding_child_orders,
                parent_log=parent_log,
            )

        # phew got there
        parent_log.msg(
            "Added parent order with ID %d %s to stack"
            % (parent_order_id, str(instrument_order))
        )
        log_successful_adding(
            list_of_child_orders=list_of_contract_orders,
            list_of_child_ids=list_of_child_order_ids,
            parent_order=instrument_order,
            parent_log=parent_log,
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

    instrument_order = create_instrument_roll_order(
        roll_spread_info=roll_spread_info, instrument_code=instrument_code
    )

    list_of_contract_orders = create_contract_roll_orders(
        data=data, roll_spread_info=roll_spread_info, instrument_order=instrument_order
    )

    return instrument_order, list_of_contract_orders


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
    diag_positions = diagPositions(data)
    diag_contracts = dataContracts(data)
    diag_prices = diagPrices(data)

    priced_contract_id = diag_contracts.get_priced_contract_id(instrument_code)
    forward_contract_id = diag_contracts.get_forward_contract_id(instrument_code)

    contract = futuresContract(instrument_code, priced_contract_id)

    position_in_priced = diag_positions.get_position_for_contract(contract)

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


def create_instrument_roll_order(
    roll_spread_info: rollSpreadInformation, instrument_code: str
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


def create_contract_roll_orders(
    data: dataBlob,
    roll_spread_info: rollSpreadInformation,
    instrument_order: instrumentOrder,
) -> listOfOrders:
    diag_positions = diagPositions(data)
    instrument_code = instrument_order.instrument_code

    if roll_spread_info.position_in_priced == 0:
        return missing_order

    if diag_positions.is_roll_state_force(instrument_code):
        contract_orders = create_contract_orders_spread(roll_spread_info)

    elif diag_positions.is_roll_state_force_outright(instrument_code):
        contract_orders = create_contract_orders_outright(roll_spread_info)

    else:
        log = instrument_order.log_with_attributes(data.log)
        roll_state = diag_positions.get_roll_state(instrument_code)
        log.warn("Roll state %s is unexpected, might have changed" % str(roll_state))
        return missing_order

    contract_orders = allocate_algo_to_list_of_contract_orders(
        data, contract_orders, instrument_order
    )

    return contract_orders


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
