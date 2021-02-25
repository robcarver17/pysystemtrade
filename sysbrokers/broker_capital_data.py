
from sysobjects.spot_fx_prices import listOfCurrencyValues

from sysdata.production.capital import capitalData
from syslogdiag.log import logtoscreen, logger


class brokerCapitalData(capitalData):
    def __init__(self,  log: logger=logtoscreen("brokerCapitalData")):
        super().__init__(log=log)

    def get_account_value_across_currency_across_accounts(self) -> listOfCurrencyValues:
        raise NotImplementedError

