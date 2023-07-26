from sysexecution.algos.algo_market import algoMarket
from sysexecution.orders.broker_orders import (
    snap_mkt_type,
    snap_mid_type,
    snap_prim_type,
    brokerOrderType,
)


class algoSnapMkt(algoMarket):
    @property
    def order_type_to_use(self) -> brokerOrderType:
        return snap_mkt_type


## THIS ARE PROVIDED FOR COMPLETENESS, BUT SINCE EXECUTION ISN'T GUARANTEED
##    MIGHT NOT BE BEST TO USE AS A SUBSTITUTE FOR A MARKET ORDER AS WE ARE
##    DOING HERE


### NOT RECOMMENDED TO USE,
class algoSnapMid(algoMarket):
    @property
    def order_type_to_use(self) -> brokerOrderType:
        return snap_mid_type


### NOT RECOMMENDED TO USE,
class algoSnapPrim(algoMarket):
    @property
    def order_type_to_use(self) -> brokerOrderType:
        return snap_prim_type
