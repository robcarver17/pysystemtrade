
from sysbrokers.IB.ib_connection import connectionIB
from sysbrokers.IB.client.ib_accounting_client import ibAccountingClient

from sysdata.production.capital import capitalData
from syslogdiag.log import logtoscreen, logger


class ibCapitalData(capitalData):
    def __init__(self, ibconnection: connectionIB, log: logger=logtoscreen("ibFxPricesData")):
        super().__init__(log=log)
        self._ibconnection = ibconnection

    @property
    def ibconnection(self) -> connectionIB:
        return self._ibconnection

    @property
    def ib_client(self) -> ibAccountingClient:
        client = getattr(self, "_ib_client", None)
        if client is None:
             client = self._ib_client = ibAccountingClient(ibconnection=self.ibconnection,
                                        log = self.log)

        return client

    def __repr__(self):
        return "IB capital data"

    def get_account_value_across_currency_across_accounts(self) -> list:
        return self.ib_client.broker_get_account_value_across_currency_across_accounts()


    """
    Can add other functions not in parent class to get IB specific stuff which could be required for
      strategy decomposition
    """
