from collections import namedtuple
from typing import List
import datetime
from dataclasses import dataclass

from syscore.pandas.pdutils import make_df_from_list_of_named_tuple


@dataclass()
class SimpleOrder:
    ### Simple order, suitable for use in simulation, but not complex enough for production

    ## Could share code, but too complicated
    quantity: int
    limit_price: float = None

    @property
    def is_market_order(self):
        if self.limit_price is None:
            return True

    @property
    def is_zero_order(self) -> bool:
        return self.quantity == 0

    @classmethod
    def zero_order(cls):
        return cls(quantity=0)


zero_order = SimpleOrder.zero_order()


class ListOfSimpleOrders(list):
    def __init__(self, list_of_orders: List[SimpleOrder]):
        super().__init__(list_of_orders)

    def remove_zero_orders(self):
        new_list = [order for order in self if not order.is_zero_order]
        return ListOfSimpleOrders(new_list)

    def contains_no_orders(self):
        return len(self.remove_zero_orders()) == 0


_SimpleOrderWithDateAsTuple = namedtuple(
    "_SimpleOrderWithDateAsTuple", ["submit_date", "quantity", "limit_price"]
)


class SimpleOrderWithDate(SimpleOrder):
    def __init__(
        self, quantity: int, submit_date: datetime.datetime, limit_price: float = None
    ):
        super().__init__(quantity=quantity, limit_price=limit_price)
        self.submit_date = submit_date

    def __repr__(self):
        if self.limit_price is None:
            limit_price_str = "MarketOrder"
        else:
            limit_price_str = str(self.limit_price)
        return "SimpleOrderWithDate(quantity=%d, limit_price=%s, date=%s)" % (
            self.quantity,
            limit_price_str,
            str(self.submit_date),
        )

    @classmethod
    def zero_order(cls, submit_date: datetime.datetime):
        return cls(quantity=0, submit_date=submit_date)

    def _as_tuple(self):
        return _SimpleOrderWithDateAsTuple(
            submit_date=self.submit_date,
            quantity=self.quantity,
            limit_price=self.limit_price,
        )


class ListOfSimpleOrdersWithDate(ListOfSimpleOrders):
    def __init__(self, list_of_orders: List[SimpleOrderWithDate]):
        super().__init__(list_of_orders)

    def as_pd_df(self):
        return make_df_from_list_of_named_tuple(
            _SimpleOrderWithDateAsTuple,
            self._as_list_of_named_tuples(),
            field_name_for_index="submit_date",
        )

    def _as_list_of_named_tuples(self) -> list:
        return [order._as_tuple() for order in self]


def empty_list_of_orders_with_date() -> ListOfSimpleOrdersWithDate:
    return ListOfSimpleOrdersWithDate([])
