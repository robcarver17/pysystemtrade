from sysdata.base_data import baseData
from syscore.objects import missing_data, missing_contract, arg_not_supplied
from syslogdiag.log import logtoscreen
from sysdata.private_config import get_private_then_default_key_value
from sysbrokers.IB.ib_connection import get_broker_account

class ibMiscData(baseData):
    def __init__(self, ibconnection, log=logtoscreen(
            "ibFuturesContractPriceData")):
        self.ibconnection = ibconnection
        super().__init__(log=log)

    def __repr__(self):
        return "IB misc data %s" % str(self.ibconnection)

    def get_broker_clientid(self):
        return self.ibconnection.ib.client.clientId

    def get_broker_account(self):
        broker_account = get_broker_account()
        return broker_account

    def get_broker_name(self):
        return "IB"

    def broker_fx_balances(self):
        return self.ibconnection.broker_fx_balances()

    def broker_fx_market_order(
            self,
            trade,
            ccy1,
            account=arg_not_supplied,
            ccy2="USD"):
        result = self.ibconnection.broker_fx_market_order(
            trade, ccy1, ccy2=ccy2, account=account
        )

        return result
