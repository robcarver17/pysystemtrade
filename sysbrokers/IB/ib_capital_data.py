
from sysbrokers.IB.ib_connection import connectionIB
from sysbrokers.IB.client.ib_accounting_client import ibAccountingClient
from sysbrokers.broker_capital_data import brokerCapitalData
from sysobjects.spot_fx_prices import listOfCurrencyValues

from syslogdiag.logger import logger
from syslogdiag.log_to_screen import logtoscreen


class ibCapitalData(brokerCapitalData):
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

    def get_account_value_across_currency_across_accounts(self) -> listOfCurrencyValues:
        return self.ib_client.broker_get_account_value_across_currency_across_accounts()


    """
    Can add other functions not in parent class to get IB specific stuff which could be required for
      strategy decomposition
    """
