import datetime
from typing import Union
from syscore.genutils import same_sign
from systems.accounts.order_simulator.fills_and_orders import (
    ListOfSimpleOrdersAndResultingFill,
    fill_list_of_simple_orders,
)
from systems.accounts.order_simulator.simple_orders import (
    ListOfSimpleOrdersWithDate,
    SimpleOrderWithDate,
    empty_list_of_orders_with_date,
)
from systems.provided.mr.create_limit_orders import create_limit_orders_for_mr_data
from systems.provided.mr.data_and_constants import (
    Mr_Trading_Flags,
    CLOSE_MR_POSITIONS,
    MRDataAtIDXPoint,
)
from systems.provided.mr.forecasting import calculate_capped_scaled_attenuated_forecast


## FIXME - PRICE FRACTION ISSUES/ LARGE FUND ISSUES


def generate_mr_orders_and_fill_at_idx_point(
    current_position: int,
    current_datetime: datetime.datetime,
    data_for_idx: MRDataAtIDXPoint,
) -> ListOfSimpleOrdersAndResultingFill:

    list_of_orders = create_orders_from_mr_data(
        current_position=current_position,
        current_datetime=current_datetime,
        data_for_idx=data_for_idx,
    )

    next_datetime = data_for_idx.next_datetime
    next_hourly_price = data_for_idx.next_hourly_price

    fill = fill_list_of_simple_orders(
        list_of_orders, market_price=next_hourly_price, fill_datetime=next_datetime
    )

    return ListOfSimpleOrdersAndResultingFill(list_of_orders=list_of_orders, fill=fill)


def create_orders_from_mr_data(
    current_position: int,
    current_datetime: datetime.datetime,
    data_for_idx: MRDataAtIDXPoint,
) -> ListOfSimpleOrdersWithDate:

    optimal_unrounded_position = derive_optimal_unrounded_position(
        data_for_idx=data_for_idx
    )
    if optimal_unrounded_position is CLOSE_MR_POSITIONS:
        ## market order to close positions
        return list_with_dated_closing_market_order(
            current_position=current_position, current_datetime=current_datetime
        )
    list_of_orders = create_orders_for_mr_data_if_not_closing(
        optimal_unrounded_position=optimal_unrounded_position,
        current_datetime=current_datetime,
        current_position=current_position,
        data_for_idx=data_for_idx,
    )

    return list_of_orders


def derive_optimal_unrounded_position(
    data_for_idx: MRDataAtIDXPoint,
) -> Union[int, Mr_Trading_Flags]:

    capped_scaled_attenuated_forecast = calculate_capped_scaled_attenuated_forecast(
        data_for_idx=data_for_idx
    )
    current_conditioner_for_forecast = data_for_idx.conditioning_forecast
    if not same_sign(
        capped_scaled_attenuated_forecast, current_conditioner_for_forecast
    ):
        ## Market order to close positions
        return CLOSE_MR_POSITIONS

    avg_abs_forecast = data_for_idx.avg_abs_forecast
    average_position = data_for_idx.average_position

    optimal_unrounded_position = average_position * (
        capped_scaled_attenuated_forecast / avg_abs_forecast
    )

    return optimal_unrounded_position


def list_with_dated_closing_market_order(
    current_position: int, current_datetime: datetime.datetime
) -> ListOfSimpleOrdersWithDate:
    if current_position == 0:
        return empty_list_of_orders_with_date()

    closing_dated_market_order = SimpleOrderWithDate(
        quantity=-current_position, submit_date=current_datetime
    )
    return ListOfSimpleOrdersWithDate([closing_dated_market_order])


def create_orders_for_mr_data_if_not_closing(
    optimal_unrounded_position: float,
    current_position: int,
    current_datetime: datetime.datetime,
    data_for_idx: MRDataAtIDXPoint,
) -> ListOfSimpleOrdersWithDate:
    rounded_optimal_position = round(optimal_unrounded_position)

    diff_to_current = abs(rounded_optimal_position - current_position)

    if diff_to_current > 1:
        ## Trade straight to optimal with market order
        return list_with_single_dated_market_order_to_trade_to_optimal(
            current_position=current_position,
            rounded_optimal_position=rounded_optimal_position,
            current_datetime=current_datetime,
        )

    list_of_orders = create_limit_orders_for_mr_data(
        data_for_idx=data_for_idx,
        current_datetime=current_datetime,
        current_position=current_position,
    )

    return list_of_orders


def list_with_single_dated_market_order_to_trade_to_optimal(
    rounded_optimal_position: int,
    current_position: int,
    current_datetime: datetime.datetime,
) -> ListOfSimpleOrdersWithDate:

    required_trade = rounded_optimal_position - current_position
    dated_market_order = SimpleOrderWithDate(
        quantity=required_trade, submit_date=current_datetime
    )
    return ListOfSimpleOrdersWithDate([dated_market_order])
