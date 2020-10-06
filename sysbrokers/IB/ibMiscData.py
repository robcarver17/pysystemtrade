from syscore.objects import missing_data, missing_contract, arg_not_supplied
from syslogdiag.log import logtoscreen
from sysdata.private_config import get_private_then_default_key_value


class ibMiscData(object):
    def __init__(self, ibconnection, log=logtoscreen(
            "ibFuturesContractPriceData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB misc data %s" % str(self.ibconnection)

    def get_broker_clientid(self):
        return self.ibconnection.ib.client.clientId

    def get_broker_account(self):
        account_id = get_private_then_default_key_value(
            "broker_account", raise_error=False
        )
        if account_id is missing_data:
            return arg_not_supplied
        else:
            return account_id

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
