from sysdata.futures.contracts import futuresContractData
from sysdata.data_blob import dataBlob
from sysobjects.contracts import futuresContract

from syslogging.logger import *


class brokerFuturesContractCommissionData(futuresContractData):
    def __init__(self, data: dataBlob, log=get_logger("brokerFuturesContractCommissionData")):
        super().__init__(log=log)
        self._data = data

    def get_commission_for_contract(self, contract: futuresContract) -> float:
        raise NotImplementedError

    @property
    def data(self):
        return self._data
