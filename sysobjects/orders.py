from dataclasses import dataclass

@dataclass()
class SimpleOrder:
    ### Simple order, suitable for use in simulation, but not complex enough for production

    ## Could share code, but too complicated
    trade: int
    limit_price: float = None

    def is_market_order(self):
        if self.limit_price is None:
            return True


