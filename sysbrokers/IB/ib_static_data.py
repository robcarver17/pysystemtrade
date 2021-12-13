from syslogdiag.log_to_screen import logtoscreen
from sysbrokers.IB.client.ib_client import ibClient
from sysbrokers.IB.ib_connection import connectionIB
from sysbrokers.broker_static_data import brokerStaticData


class ibStaticData(brokerStaticData):
    def __init__(self, ibconnection: connectionIB, log=logtoscreen("ibStaticData")):
        self._ibconnection = ibconnection
        super().__init__(log=log)

    def __repr__(self):
        return "IB static data %s" % str(self.ib_client)

    @property
    def ibconnection(self) -> connectionIB:
        return self._ibconnection

    @property
    def ib_client(self) -> ibClient:
        client = getattr(self, "_ib_client", None)
        if client is None:
            client = self._ib_client = ibClient(
                ibconnection=self.ibconnection, log=self.log
            )

        return client

    def get_broker_clientid(self) -> int:
        return self.ib_client.client_id

    def get_broker_account(self) -> str:
        broker_account = self.ibconnection.account
        return broker_account

    def get_broker_name(self) -> str:
        return "IB"
