from syscore.objects import arg_not_supplied
from sysdata.base_data import baseData
from sysbrokers.broker_trade import brokerTrade

from syslogdiag.log_to_screen import logtoscreen


### generic base class for FX handling
class brokerFxHandlingData(baseData):
    def __init__(self, log=logtoscreen("brokerFXHandlingData")):
        super().__init__(log=log)

    def broker_fx_balances(self, account_id: str = arg_not_supplied) -> dict:
        raise NotImplementedError

    def broker_fx_market_order(
        self,
        trade: float,
        ccy1: str,
        account_id: str = arg_not_supplied,
        ccy2: str = "USD",
    ) -> brokerTrade:

        raise NotImplementedError
