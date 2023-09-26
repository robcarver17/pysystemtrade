from sysexecution.algos.algo_market import algoMarket
from sysexecution.orders.broker_orders import brokerOrderType, adaptive_mkt_type


class algoAdaptiveMkt(algoMarket):

    # Adaptive market orders should eventually execute, but might take a while
    # This allows re-using the market order trade management logic, but without timing out
    ORDER_TIME_OUT = float("inf")

    @property
    def order_type_to_use(self) -> brokerOrderType:
        return adaptive_mkt_type
