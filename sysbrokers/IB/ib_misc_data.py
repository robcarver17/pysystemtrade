from sysdata.base_data import baseData
from syscore.objects import  arg_not_supplied
from syslogdiag.log import logtoscreen
from sysbrokers.IB.client.ib_fx_client import ibFxClient
from sysbrokers.IB.ib_connection import get_broker_account, connectionIB
from sysbrokers.IB.ib_translate_broker_order_objects import tradeWithContract

class ibMiscData(baseData):
    def __init__(self, ibconnection: connectionIB, log=logtoscreen(
            "ibFuturesContractPriceData")):
        self._ibconnection = ibconnection
        super().__init__(log=log)

    def __repr__(self):
        return "IB misc data %s" % str(self.ib_client)


    @property
    def ibconnection(self) -> connectionIB:
        return self._ibconnection

    @property
    def ib_client(self) -> ibFxClient:
        client = getattr(self, "_ib_client", None)
        if client is None:
             client = self._ib_client = ibFxClient(ibconnection=self.ibconnection,
                                                   log = self.log)

        return client

    def get_broker_clientid(self) -> int:
        return self.ib_client.ib.client.clientId

    def get_broker_account(self) -> str:
        broker_account = get_broker_account()
        return broker_account

    def get_broker_name(self)-> str:
        return "IB"

    def broker_fx_balances(self) -> dict:
        return self.ib_client.broker_fx_balances()

    def broker_fx_market_order(
            self,
            trade,
            ccy1,
            account=arg_not_supplied,
            ccy2="USD") -> tradeWithContract:

        submitted_fx_trade = self.ib_client.broker_fx_market_order(
            trade, ccy1, ccy2=ccy2, account=account
        )

        return submitted_fx_trade
