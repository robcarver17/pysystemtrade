from sysbrokers.IB.ib_connection import connectionIB
from sysbrokers.IB.ib_orders import ibExecutionStackData
from sysbrokers.IB.ib_translate_broker_order_objects import tradeWithContract
from sysbrokers.broker_contract_commission_data import (
    brokerFuturesContractCommissionData,
)
from sysdata.data_blob import dataBlob
from sysexecution.orders.broker_orders import brokerOrder
from sysobjects.contracts import futuresContract

from syslogging.logger import *
from syscore.genutils import quickTimer
from sysobjects.spot_fx_prices import currencyValue


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
        return "IB Futures commissions data %s" % str(self.ibconnection)

    @property
    def ibconnection(self) -> connectionIB:
        return self._ibconnection

    @property
    def execution_stack(self) -> ibExecutionStackData:
        return self.data.broker_execution_stack

    def get_commission_for_contract(
        self, futures_contract: futuresContract
    ) -> currencyValue:
        instrument_code = futures_contract.instrument_code
        contract_date = futures_contract.contract_date.list_of_date_str[0]

        broker_order = brokerOrder(
            test_commission_strategy, instrument_code, contract_date, size_of_test_trade
        )

        order = self.execution_stack.what_if_order(broker_order)

        timer = quickTimer(5)
        comm_currency_value = currencyValue(currency="", value=0)
        while timer.unfinished:
            try:
                comm_currency_value = get_commission_and_currency_from_ib_order(order)
            except:
                continue

        return comm_currency_value


def get_commission_and_currency_from_ib_order(
    ib_order: tradeWithContract,
) -> currencyValue:
    return currencyValue(
        value=ib_order.trade.commission / size_of_test_trade,
        currency=ib_order.trade.commissionCurrency,
    )


test_commission_strategy = "testCommmission"  ## whatever not put on stack
size_of_test_trade = 10  ## arbitrary
