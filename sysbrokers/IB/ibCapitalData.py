import pandas as pd
from sysdata.production.capital import capitalData
from syslogdiag.log import logtoscreen
from syscore.fileutils import get_filename_for_package
from syscore.objects import missing_file, missing_instrument


class ibCapitalData(capitalData):
    def __init__(self, ibconnection, log=logtoscreen("ibFxPricesData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB capital data"

    def get_current_total_capital(self):
        return self.ibconnection.broker_get_total_account_value()

    """
    Can add other functions not in parent class to get IB specific stuff which could be required for
      strategy decomposition
    """
