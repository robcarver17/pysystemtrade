from collections import namedtuple
import datetime
from typing import Union


from sysobjects.fills import Fill, ListOfFills, empty_fill
from systems.accounts.order_simulator.simple_orders import (
    ListOfSimpleOrders,
    SimpleOrder,
    SimpleOrderWithDate,
    empty_list_of_orders_with_date,
)


def fill_list_of_simple_orders(
    list_of_orders: ListOfSimpleOrders,
    fill_datetime: datetime.datetime,
    market_price: float,
) -> Fill:
    list_of_fills = [
        fill_from_simple_order(
            simple_order=simple_order,
            fill_datetime=fill_datetime,
            market_price=market_price,
        )
        for simple_order in list_of_orders
    ]
    list_of_fills = ListOfFills(list_of_fills)  ## will remove unfilled

    if len(list_of_fills) == 0:
        return empty_fill(fill_datetime)
    elif len(list_of_fills) == 1:
        return list_of_fills[0]
    else:
        raise Exception(
            "List of orders %s has produced more than one fill %s!"
            % (str(list_of_orders), str(list_of_orders))
        )


def fill_from_simple_order(
    simple_order: SimpleOrder,
    market_price: float,
    fill_datetime: datetime.datetime,
) -> Fill:
    if simple_order.is_zero_order:
        return empty_fill(fill_datetime)

    elif simple_order.is_market_order:
        fill = fill_from_simple_market_order(
            simple_order,
            market_price=market_price,
            fill_datetime=fill_datetime,
        )
    else:
        ## limit order
        fill = fill_from_simple_limit_order(
            simple_order, market_price=market_price, fill_datetime=fill_datetime
        )

    return fill


def fill_from_simple_limit_order(
    simple_order: Union[SimpleOrder, SimpleOrderWithDate],
    market_price: float,
    fill_datetime: datetime.datetime,
) -> Fill:
    limit_price = simple_order.limit_price
    if simple_order.quantity > 0:
        if limit_price > market_price:
            return Fill(
                fill_datetime,
                simple_order.quantity,
                limit_price,
                price_requires_slippage_adjustment=False,
            )

    if simple_order.quantity < 0:
        if limit_price < market_price:
            return Fill(
                fill_datetime,
                simple_order.quantity,
                limit_price,
                price_requires_slippage_adjustment=True,
            )

    return empty_fill(fill_datetime)


def fill_from_simple_market_order(
    simple_order: Union[SimpleOrder, SimpleOrderWithDate],
    market_price: float,
    fill_datetime: datetime.datetime,
) -> Fill:
    return Fill(
        fill_datetime,
        simple_order.quantity,
        market_price,
        price_requires_slippage_adjustment=True,
    )


ListOfSimpleOrdersAndResultingFill = namedtuple(
    "ListOfSimpleOrdersAndResultingFill", ["list_of_orders", "fill"]
)


def empty_list_of_orders_with_no_fills(
    fill_datetime: datetime.datetime,
) -> ListOfSimpleOrdersAndResultingFill:
    return ListOfSimpleOrdersAndResultingFill(
        empty_list_of_orders_with_date(), empty_fill(fill_datetime)
    )
