"""
Simplest possible execution method, one market order
"""
from copy import copy
from syscore.objects import missing_order
from sysproduction.data.broker import dataBroker

from sysexecution.algos.algo import Algo
from sysexecution.algos.common_functions import (
    post_trade_processing,
    MESSAGING_FREQUENCY,
    cancel_order,
    file_log_report_market_order,
)
from sysdata.data_blob import dataBlob
from sysexecution.orders.contract_orders import contractOrder
from sysexecution.order_stacks.broker_order_stack import orderWithControls
from sysexecution.orders.broker_orders import market_order_type


class algoLimit(Algo):
    """
    Submit a limit order
    """

    @property
    def blocking_algo_requires_management(self) -> bool:
        return False

    def submit_trade(self) -> orderWithControls:
        contract_order = self.contract_order
        broker_order_with_controls = (
            self.get_and_submit_broker_order_for_contract_order(
                contract_order, order_type=market_order_type
            )
        )

        return broker_order_with_controls

    def manage_trade(
        self, broker_order_with_controls: orderWithControls
    ) -> orderWithControls:
        raise Exception("Limit order shouldn't be managed")

