from syscore.objects import missing_data
from syslogdiag.log import logtoscreen
from sysdata.private_config import get_private_then_default_key_value

class ibMiscData(object):
    def __init__(self, ibconnection, log=logtoscreen("ibFuturesContractPriceData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB misc data %s" % str(self.ibconnection)

    def get_broker_clientid(self):
        return self.ibconnection.ib.client.clientId

    def get_broker_account(self):
        account_id = get_private_then_default_key_value("broker_account", raise_error=False)
        if account_id is missing_data:
            return ''
        else:
            return account_id

    def get_broker_name(self):
        return "IB"
