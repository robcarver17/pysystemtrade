
from sysbrokers.IB.ib_connection import connectionIB
from sysbrokers.IB.ib_orders import ibExecutionStackData
from sysdata.data_blob import dataBlob
from sysexecution.orders.broker_orders import brokerOrder
from sysobjects.contracts import futuresContract

from syslogging.logger import *
from sysbrokers.broker_commissions import brokerFuturesContractCommissionData

class ibFuturesContractCommissionData(brokerFuturesContractCommissionData):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This gets HISTORIC data from interactive brokers. It is blocking code
    In a live production system it is suitable for running on a daily basis to get end of day prices

    """

    def __init__(
        self,
        ibconnection: connectionIB,
        data: dataBlob,
        log=get_logger("ibFuturesContractCommissionData"),
    ):
        super().__init__(log=log, data=data)
        self._ibconnection = ibconnection

    def __repr__(self):
        return "IB Futures commissions data %s" % str(self.ib_client)

    @property
    def ibconnection(self) -> connectionIB:
        return self._ibconnection

    @property
    def execution_stack(self) -> ibExecutionStackData:
        return self.data.broker_execution_stack

    def get_commission_for_contract(self, futures_contract: futuresContract) -> float:
        ## FOR NOW DO NOT RUN IF ANYTHING ELSE IS RUNNING
        ## NEEDS CODE TO TAKE THE TEST STRATEGY OFF THE STACK WHEN RETURNING ORDERS
        size_of_test_trade = 10
        instrument_code = futures_contract.instrument_code
        contract_date = futures_contract.contract_date.list_of_date_str[0]

        broker_order =brokerOrder(test_commission_strategy, instrument_code, contract_date,
                    size_of_test_trade)

        order = self.execution_stack.put_what_if_order_on_stack(broker_order)

        while not self.execution_stack.is_completed(order.order.order_id):
            ## could last forever!
            continue

        order_from_stack = self.execution_stack.get_order_with_id_from_stack(order_id=order.order.order_id)
        return order_from_stack.commission / 10.0

test_commission_strategy = "testCommmission"
