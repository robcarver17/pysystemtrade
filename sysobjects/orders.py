from dataclasses import dataclass
from syscore.objects import arg_not_supplied, named_object

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
        return self.quantity==0

    @classmethod
    def zero_order(cls):
        return cls(quantity = 0)

zero_order = SimpleOrder.zero_order()

class ListOfSimpleOrders(list):
    def remove_zero_orders(self):
        new_list = [order for order in self if not order.is_zero_order]
        return ListOfSimpleOrders(new_list)
