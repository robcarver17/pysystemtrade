from sysexecution.algos.algo_market import algoMarket
from sysexecution.orders.broker_orders import brokerOrderType, adaptive_mkt_type


class algoAdaptiveMkt(algoMarket):
    @property
    def order_type_to_use(self) -> brokerOrderType:
        return adaptive_mkt_type
