from sysdata.base_data import baseData
from syslogdiag.log_to_screen import logtoscreen


class brokerStaticData(baseData):
    def __init__(self, log=logtoscreen("brokerStaticData")):
        super().__init__(log=log)

    def get_broker_clientid(self) -> int:
        raise NotImplementedError

    def get_broker_account(self) -> str:
        raise NotImplementedError

    def get_broker_name(self) -> str:
        raise NotImplementedError
