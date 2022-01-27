from sysobjects.spot_fx_prices import listOfCurrencyValues

from syscore.objects import arg_not_supplied

from sysdata.production.capital import capitalData
from syslogdiag.logger import logger
from syslogdiag.log_to_screen import logtoscreen


class brokerCapitalData(capitalData):
    def __init__(self, log: logger = logtoscreen("brokerCapitalData")):
        super().__init__(log=log)

    def get_account_value_across_currency(
        self, account_id: str = arg_not_supplied
    ) -> listOfCurrencyValues:
        raise NotImplementedError

    def get_excess_liquidity_value_across_currency(self,
                                                   account_id: str = arg_not_supplied
                                                   )-> listOfCurrencyValues:
        raise NotImplementedError
